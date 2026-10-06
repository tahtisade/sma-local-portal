import base64
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from sma.heater_meter_service import DailyEnergy, HeaterMeterService, decode_phase


def packet(watts=100, voltage=2364, current=218):
    return base64.b64encode(voltage.to_bytes(2, "big") +
                            current.to_bytes(3, "big") +
                            watts.to_bytes(3, "big")).decode()


def local_time(value):
    return datetime.fromisoformat(value).replace(
        tzinfo=ZoneInfo("Europe/Helsinki")).timestamp()


class MeterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.ledger = DailyEnergy(self.path / "daily.db", "meter-a")

    def test_verified_scaling(self):
        self.assertEqual(decode_phase(packet(11)),
                         {"voltage": 236.4, "current": 0.218, "power": 11})
        service = HeaterMeterService({})
        service.ledger = self.ledger
        service.ingest({"dps": {"1": 512701}})
        self.assertEqual(service.get_status()["total_energy_kwh"], 5127.01)
        self.assertIsNone(service.get_status()["power_kw"])

    def test_first_day_and_restart(self):
        now = local_time("2026-10-04T20:00:00")
        self.assertEqual(self.ledger.observe(5127.01, now), (0, True, "2026-10-04"))
        new = DailyEnergy(self.path / "daily.db", "meter-a")
        energy, partial, _ = new.observe(5128.01, now + 60)
        self.assertAlmostEqual(energy, 1)
        self.assertTrue(partial)

    def test_midnight_and_long_gap(self):
        now = local_time("2026-10-04T23:59:50")
        self.ledger.observe(100, now)
        energy, partial, day = self.ledger.observe(100.02, now + 30)
        self.assertAlmostEqual(energy, .02)
        self.assertFalse(partial)
        self.assertEqual(day, "2026-10-05")
        self.assertEqual(self.ledger.observe(102, now + 90000)[1], True)

    def test_reset_no_negative_daily_energy(self):
        now = local_time("2026-10-04T20:00:00")
        self.ledger.observe(100, now)
        self.ledger.observe(101, now + 30)
        self.assertEqual(self.ledger.observe(0, now + 60)[:2], (1, True))
        self.assertEqual(self.ledger.observe(.5, now + 90)[:2], (1.5, True))

    def test_replacement_meter_has_own_baseline(self):
        now = local_time("2026-10-04T20:00:00")
        self.ledger.observe(100, now)
        other = DailyEnergy(self.path / "daily.db", "meter-b")
        self.assertEqual(other.observe(20000, now)[:2], (0, True))

    def test_dst_uses_local_date(self):
        now = datetime.fromisoformat("2026-10-25T03:59:50+03:00").timestamp()
        self.ledger.observe(100, now)
        # Fall-back transition remains the same Helsinki day.
        energy, _, day = self.ledger.observe(101, now + 30)
        self.assertEqual((energy, day), (1, "2026-10-25"))

    def test_staleness_per_phase_and_disconnect(self):
        service = HeaterMeterService({"stale_seconds": 90})
        service.ledger = self.ledger
        with patch("sma.heater_meter_service.time.monotonic", return_value=0):
            service.ingest({"dps": {"1": 10000, "6": packet(),
                                    "7": packet(200), "8": packet(300)}})
            self.assertEqual(service.get_status()["power_kw"], .6)
        with patch("sma.heater_meter_service.time.monotonic", return_value=100):
            service.ingest({"dps": {"1": 10000, "6": packet()}})
            self.assertIsNone(service.get_status()["power_kw"])
            self.assertEqual(service.get_status()["total_energy_kwh"], 100)
            service.connected = False
            self.assertIsNone(service.get_status()["total_energy_kwh"])

    def test_zero_is_valid_measurement(self):
        service = HeaterMeterService({})
        service.ledger = self.ledger
        service.ingest({"dps": {"1": 0, **{k: packet(0) for k in ("6", "7", "8")}}})
        self.assertEqual(service.get_status()["power_kw"], 0)
        self.assertEqual(service.get_status()["total_energy_kwh"], 0)

    def test_protocol_errors_and_bad_phase(self):
        service = HeaterMeterService({})
        service.ingest(None)
        service.ingest({"Err": 904})
        with self.assertRaises(RuntimeError):
            service.ingest({"Err": 901})
        with self.assertRaises(ValueError):
            decode_phase("AAAA")
        with self.assertRaises(ValueError):
            service.ingest({"dps": {"1": float("nan")}})

    def test_missing_persistence_does_not_show_daily_zero(self):
        service = HeaterMeterService({})
        service.ledger = DailyEnergy(self.path / "missing" / "daily.db", "meter")
        service.ingest({"dps": {"1": 100}})
        self.assertEqual(service.get_status()["total_energy_kwh"], 1)
        self.assertIsNone(service.get_status()["daily_energy_kwh"])

    def test_worker_reads_initial_packet_and_closes_connection(self):
        config_file = self.path / "devices.json"
        config_file.write_text(json.dumps([{"name": "test", "id": "test-id",
                                           "ip": "127.0.0.1", "key": "dummy"}]))
        service = HeaterMeterService({"devices_file": str(config_file),
                                      "device_name": "test",
                                      "daily_state_file": str(self.path / "worker.db")})
        calls = []

        class FakeDevice:
            # No relay-write methods: any unexpected control call fails.
            def __init__(self, *args, **kwargs): pass
            def set_socketPersistent(self, value): pass
            def set_socketTimeout(self, value): pass
            def set_socketRetryLimit(self, value): pass
            def status(self):
                calls.append("status")
                return {"dps": {"1": 512701, **{k: packet() for k in ("6", "7", "8")}}}
            def receive(self):
                service.stop_event.set()
                return None
            def close(self): calls.append("close")

        import types
        with patch.dict("sys.modules", {"tinytuya": types.SimpleNamespace(Device=FakeDevice)}):
            service.run()
        self.assertEqual(calls, ["status", "close"])
        self.assertEqual(service.get_status()["power_kw"], .3)

    def test_bad_timezone_does_not_break_status_api(self):
        service = HeaterMeterService({"timezone": "invalid/timezone"})
        self.assertEqual(service.get_status()["status"], "offline")
        with self.assertRaises(ValueError):
            service._load_device()

    def test_worker_reconnects_after_failure(self):
        config_file = self.path / "devices.json"
        config_file.write_text(json.dumps([{"name": "test", "id": "test-id",
                                           "ip": "127.0.0.1", "key": "dummy"}]))
        service = HeaterMeterService({"devices_file": str(config_file),
                                      "device_name": "test",
                                      "daily_state_file": str(self.path / "retry.db")})
        instances = []
        closed = []

        class FakeDevice:
            def __init__(self, *args, **kwargs):
                self.number = len(instances)
                instances.append(self)
            def set_socketPersistent(self, value): pass
            def set_socketTimeout(self, value): pass
            def set_socketRetryLimit(self, value): pass
            def status(self):
                if self.number == 0:
                    raise OSError("disconnected")
                return {"dps": {"1": 100, **{k: packet() for k in ("6", "7", "8")}}}
            def receive(self):
                service.stop_event.set()
                return None
            def close(self): closed.append(self.number)

        import types
        with patch.dict("sys.modules", {"tinytuya": types.SimpleNamespace(Device=FakeDevice)}), \
                patch.object(service.stop_event, "wait", return_value=False):
            service.run()
        self.assertEqual(closed, [0, 1])
        self.assertTrue(service.get_status()["connected"])


if __name__ == "__main__":
    unittest.main()
