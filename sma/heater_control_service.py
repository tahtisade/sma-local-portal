import json
import math
import os
import threading
from datetime import datetime


class HeaterControlService:

    ALLOWED_MODES = {
        "off",
        "pv",
        "pv_price",
        "price",
        "on",
    }

    MIN_POWER = 0
    MAX_POWER = 6000
    MIN_TEMPERATURE_TARGET = 40.0
    MAX_TEMPERATURE_TARGET = 71.0

    def __init__(
        self,
        config_file="heater_control.json",
        default_mode="pv_price",
        default_spot_price_limit=10.0,
        default_max_power=6000,
        default_price_start="00:00",
        default_price_end="06:00",
    ):
        self.config_file = config_file
        self._lock = threading.Lock()

        self.mode = default_mode
        self.spot_price_limit = default_spot_price_limit
        self.max_power = default_max_power

        self.price_start = default_price_start
        self.price_end = default_price_end
        self.temperature_target = self.MAX_TEMPERATURE_TARGET

        self.controller_power = 0
        self.controller_reason = "UNKNOWN"
        self.controller_status = "UNKNOWN"
        self.controller_timestamp = None

        self._load()

    # ========================================================
    # TIME VALIDATION
    # ========================================================

    @staticmethod
    def _validate_time(value):

        if not isinstance(value, str):
            raise ValueError(
                "Invalid heater price time"
            )

        try:
            parsed = datetime.strptime(
                value,
                "%H:%M"
            )
        except ValueError as exc:
            raise ValueError(
                "Invalid heater price time"
            ) from exc

        return parsed.strftime("%H:%M")

    @classmethod
    def _validate_temperature_target(cls, value):
        if isinstance(value, bool):
            raise ValueError("Invalid heater temperature target")
        value = float(value)
        if not math.isfinite(value) or not cls.MIN_TEMPERATURE_TARGET <= value <= cls.MAX_TEMPERATURE_TARGET:
            raise ValueError("Heater temperature target must be 40–71 °C")
        return value

    # ========================================================
    # LOAD
    # ========================================================

    def _load(self):

        if not os.path.exists(
            self.config_file
        ):
            return

        try:
            with open(
                self.config_file,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

            if "temperature_target" in data:
                try:
                    self.temperature_target = self._validate_temperature_target(data["temperature_target"])
                except (ValueError, TypeError):
                    # A corrupt target must not silently raise the cutoff to 71 °C.
                    self.temperature_target = self.MIN_TEMPERATURE_TARGET
                    print("Invalid heater temperature target in config; using 40 °C")

            mode = data.get(
                "mode"
            )

            price_limit = data.get(
                "spot_price_limit"
            )

            max_power = data.get(
                "max_power"
            )

            price_start = data.get(
                "price_start"
            )

            price_end = data.get(
                "price_end"
            )

            if mode in self.ALLOWED_MODES:
                self.mode = mode

            if price_limit is not None:

                price_limit = float(
                    price_limit
                )

                if (
                    -100.0
                    <= price_limit
                    <= 500.0
                ):
                    self.spot_price_limit = (
                        price_limit
                    )

            if max_power is not None:

                max_power = int(
                    max_power
                )

                if (
                    self.MIN_POWER
                    <= max_power
                    <= self.MAX_POWER
                ):
                    self.max_power = (
                        max_power
                    )

            if price_start is not None:

                self.price_start = (
                    self._validate_time(
                        price_start
                    )
                )

            if price_end is not None:

                self.price_end = (
                    self._validate_time(
                        price_end
                    )
                )

        except Exception as exc:

            print(
                f"Heater control config load error: "
                f"{exc}"
            )

    # ========================================================
    # SAVE
    # ========================================================

    def _save(self, data=None):

        if data is None:
            data = self._settings()

        temp_file = (
            self.config_file
            + ".tmp"
        )

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )

        os.replace(
            temp_file,
            self.config_file
        )

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self):

        with self._lock:

            return {
                "mode": self.mode,

                "spot_price_limit": (
                    self.spot_price_limit
                ),

                "max_power": (
                    self.max_power
                ),

                "price_start": (
                    self.price_start
                ),

                "price_end": (
                    self.price_end
                ),

                "temperature_target": self.temperature_target,

                "controller_power": (
                    self.controller_power
                ),

                "controller_reason": (
                    self.controller_reason
                ),

                "controller_status": (
                    self.controller_status
                ),

                "controller_timestamp": (
                    self.controller_timestamp
                ),
            }

    # ========================================================
    # UPDATE
    # ========================================================

    def _settings(self):
        return {key: getattr(self, key) for key in (
            "mode", "spot_price_limit", "max_power", "price_start",
            "price_end", "temperature_target",
        )}

    def update(
        self, mode=None, spot_price_limit=None, max_power=None,
        price_start=None, price_end=None, temperature_target=None,
    ):
        with self._lock:
            # Validate and persist the complete candidate before changing live state.
            candidate = self._settings()
            if mode is not None:
                if mode not in self.ALLOWED_MODES:
                    raise ValueError("Invalid heater mode")
                candidate["mode"] = mode
            if spot_price_limit is not None:
                value = float(spot_price_limit)
                if not -100.0 <= value <= 500.0:
                    raise ValueError("Invalid spot price limit")
                candidate["spot_price_limit"] = value
            if max_power is not None:
                value = int(max_power)
                if not self.MIN_POWER <= value <= self.MAX_POWER:
                    raise ValueError("Invalid heater max power")
                candidate["max_power"] = value
            for key, value in (("price_start", price_start), ("price_end", price_end)):
                if value is not None:
                    candidate[key] = self._validate_time(value)
            if temperature_target is not None:
                candidate["temperature_target"] = self._validate_temperature_target(temperature_target)
            self._save(candidate)
            for key, value in candidate.items():
                setattr(self, key, value)
            return dict(candidate)

    # ========================================================
    # CONTROLLER STATUS
    # ========================================================

    def update_controller_status(
        self,
        power,
        reason,
        controller_status,
    ):

        with self._lock:

            self.controller_power = int(
                power
            )

            self.controller_reason = str(
                reason
            )

            self.controller_status = str(
                controller_status
            )

            import time

            self.controller_timestamp = (
                time.time()
            )

            return {
                "controller_power": (
                    self.controller_power
                ),

                "controller_reason": (
                    self.controller_reason
                ),

                "controller_status": (
                    self.controller_status
                ),

                "controller_timestamp": (
                    self.controller_timestamp
                ),
            }
