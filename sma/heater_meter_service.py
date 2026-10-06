"""Optional, read-only EARU meter for the PV surplus load card.

Only the verified EARU layout is supported: DPS 1 = 0.01 kWh,
DPS 6/7/8 = voltage/current/power phase packets. No relay writes.
"""

import base64
import json
import logging
import math
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LOG = logging.getLogger(__name__)


def decode_phase(value):
    raw = base64.b64decode(value, validate=True)
    if len(raw) != 8:
        raise ValueError("invalid EARU phase packet length")
    return {
        "voltage": int.from_bytes(raw[:2], "big") / 10.0,
        "current": int.from_bytes(raw[2:5], "big") / 1000.0,
        "power": int.from_bytes(raw[5:8], "big"),
    }


class DailyEnergy:
    """Persist observed counter differences, scoped to a meter and local date."""

    def __init__(self, filename, identity, timezone="Europe/Helsinki"):
        self.filename = str(filename)
        self.identity = identity
        self.timezone = ZoneInfo(timezone)

    def observe(self, total, now):
        day = datetime.fromtimestamp(now, self.timezone).date().isoformat()
        with sqlite3.connect(self.filename, timeout=2) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS heater_daily (
                identity TEXT PRIMARY KEY, day TEXT, total REAL,
                updated REAL, energy REAL, partial INTEGER)""")
            row = db.execute(
                "SELECT day, total, updated, energy, partial FROM heater_daily "
                "WHERE identity = ?", (self.identity,),
            ).fetchone()
            energy, partial = 0.0, True
            if row:
                old_day, old_total, updated, old_energy, old_partial = row
                delta = total - old_total
                gap = now - updated
                if day == old_day:
                    energy = old_energy + max(0.0, delta)
                    partial = bool(old_partial) or delta < 0 or gap < 0
                elif day > old_day:
                    # A short interval spanning midnight is allocated to the
                    # new day; this is an estimate, never an exact daily DPS.
                    if 0 <= gap <= 120 and delta >= 0:
                        energy, partial = delta, False
                else:
                    # Clock moved backwards: restart a partial local day.
                    partial = True
            db.execute(
                "INSERT OR REPLACE INTO heater_daily VALUES (?, ?, ?, ?, ?, ?)",
                (self.identity, day, total, now, energy, int(partial)),
            )
        return energy, partial, day


class HeaterMeterService:
    def __init__(self, config):
        self.config = dict(config)
        self.lock = threading.Lock()
        self.phases = {}
        self.total = None
        self.energy_updated = None
        self.energy_timestamp = None
        self.daily = None
        self.day = None
        self.partial = True
        self.connected = False
        self.error = None
        self.stale_seconds = float(config.get("stale_seconds", 90))
        try:
            self.timezone = ZoneInfo(config.get("timezone", "Europe/Helsinki"))
            self.configuration_error = None
        except (ValueError, KeyError):
            self.timezone = ZoneInfo("Europe/Helsinki")
            self.configuration_error = "invalid meter timezone"
        self.stop_event = threading.Event()
        self.thread = None
        self.ledger = None

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def _load_device(self):
        if self.configuration_error:
            raise ValueError(self.configuration_error)
        if self.config.get("driver", "earu_tuya") != "earu_tuya":
            raise ValueError("unsupported heater meter driver")
        path = Path(self.config["devices_file"]).expanduser()
        with path.open(encoding="utf-8") as stream:
            devices = json.load(stream)
        matches = [d for d in devices
                   if d.get("name") == self.config["device_name"]]
        if len(matches) != 1:
            raise ValueError("heater meter name must match exactly one device")
        cfg = matches[0]
        if not all(cfg.get(k) for k in ("id", "ip", "key")):
            raise ValueError("heater meter configuration is incomplete")
        return cfg

    def ingest(self, data):
        if not data:
            return
        if not isinstance(data, dict):
            raise ValueError("invalid meter response")
        if "Err" in data:
            if str(data["Err"]) == "904":
                return  # TinyTuya receive timeout
            raise RuntimeError("meter protocol error " + str(data["Err"]))
        dps = data.get("dps", {})
        if not isinstance(dps, dict):
            raise ValueError("invalid meter DPS")
        monotonic, now = time.monotonic(), time.time()
        # Validate the packet before changing live state.
        phases = {key: decode_phase(dps[key]) for key in ("6", "7", "8")
                  if key in dps}
        total = None
        if "1" in dps:
            if isinstance(dps["1"], bool):
                raise ValueError("invalid meter energy counter")
            total = float(dps["1"]) / 100.0
            if not math.isfinite(total) or total < 0:
                raise ValueError("invalid meter energy counter")
        daily_result = None
        if total is not None:
            try:
                daily_result = self.ledger.observe(total, now)
            except (sqlite3.Error, OSError):
                # Never silently continue a daily total without persistence.
                LOG.error("Heater meter daily energy could not be saved")
        with self.lock:
            for key, phase in phases.items():
                self.phases[key] = (phase, monotonic, now)
            if total is not None:
                self.total = total
                self.energy_updated = monotonic
                self.energy_timestamp = now
                if daily_result:
                    self.daily, self.partial, self.day = daily_result
                else:
                    self.daily, self.day = None, None
            self.connected = True
            self.error = None

    def get_status(self):
        now = time.monotonic()
        today = datetime.now(self.timezone).date().isoformat()
        with self.lock:
            phase_live = self.connected and all(
                key in self.phases and
                now - self.phases[key][1] <= self.stale_seconds
                for key in ("6", "7", "8")
            )
            energy_live = (self.connected and self.energy_updated is not None
                           and now - self.energy_updated <= self.stale_seconds)
            power = sum(self.phases[k][0]["power"] for k in ("6", "7", "8")) \
                if phase_live else None
            return {
                "enabled": True,
                "connected": self.connected,
                "power_timestamp": min(self.phases[k][2] for k in ("6", "7", "8"))
                    if all(k in self.phases for k in ("6", "7", "8")) else None,
                "total_energy_timestamp": self.energy_timestamp,
                "daily_energy_timestamp": self.energy_timestamp,
                "phase_timestamps": {key: value[2] for key, value in self.phases.items()},
                "stale_seconds": self.stale_seconds,
                "power_kw": power / 1000.0 if power is not None else None,
                "total_energy_kwh": self.total if energy_live else None,
                "daily_energy_kwh": self.daily if energy_live and self.day == today else None,
                "daily_energy_partial": self.partial,
                "daily_energy_estimated": True,
                "daily_date": self.day,
                "status": "offline" if not self.connected else
                          "live" if phase_live and energy_live else "waiting",
                "error": self.error,
            }

    def run(self):
        while not self.stop_event.is_set():
            dev = None
            try:
                # Optional dependency: a disabled integration never imports it.
                import tinytuya
                cfg = self._load_device()
                identity = cfg["id"] + ":" + self.config.get("timezone", "Europe/Helsinki")
                self.ledger = DailyEnergy(
                    Path(self.config.get("daily_state_file", "heater_meter_daily.db")).expanduser(),
                    identity, self.config.get("timezone", "Europe/Helsinki"),
                )
                dev = tinytuya.Device(cfg["id"], cfg["ip"], cfg["key"],
                                      version=float(cfg.get("version") or 3.4))
                dev.set_socketPersistent(True)
                dev.set_socketTimeout(2)
                dev.set_socketRetryLimit(1)
                initial = dev.status()
                if not initial or "Err" in initial:
                    raise RuntimeError("meter did not answer initial status query")
                with self.lock:
                    # No phase packets from an earlier connection may be reused.
                    self.phases.clear()
                    self.energy_updated = None
                    self.energy_timestamp = None
                self.ingest(initial)
                LOG.warning("Energy meter connected: %s", self.config.get("device_name", "heater"))
                heartbeat_at = time.monotonic() + 10
                query_at = time.monotonic() + 30
                answered_at = time.monotonic()
                while not self.stop_event.is_set():
                    now = time.monotonic()
                    if now >= heartbeat_at:
                        self.ingest(dev.heartbeat(nowait=True))
                        heartbeat_at = now + 10
                    if now >= query_at:
                        data = dev.status()
                        if data and "Err" not in data:
                            answered_at = time.monotonic()
                        self.ingest(data)
                        query_at = time.monotonic() + 30
                    data = dev.receive()
                    self.ingest(data)
                    if time.monotonic() - answered_at > 90:
                        raise RuntimeError("meter status queries timed out")
            except Exception as exc:
                # Do not expose exceptions containing device keys or payloads.
                with self.lock:
                    self.connected = False
                    self.error = type(exc).__name__
                LOG.warning("Energy meter %s unavailable (%s); retry in 5 s",
                            self.config.get("device_name", "heater"), type(exc).__name__)
            finally:
                if dev is not None:
                    dev.close()
            self.stop_event.wait(5)
