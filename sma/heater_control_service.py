import json
import os
import threading


class HeaterControlService:

    ALLOWED_MODES = {
        "off",
        "pv",
        "pv_price",
        "on",
    }

    MIN_POWER = 0
    MAX_POWER = 6000

    def __init__(
        self,
        config_file="heater_control.json",
        default_mode="pv_price",
        default_spot_price_limit=10.0,
        default_max_power=6000,
    ):
        self.config_file = config_file
        self._lock = threading.Lock()

        self.mode = default_mode
        self.spot_price_limit = default_spot_price_limit
        self.max_power = default_max_power

        self.controller_power = 0
        self.controller_reason = "UNKNOWN"
        self.controller_timestamp = None

        self._load()

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

            mode = data.get(
                "mode"
            )

            price_limit = data.get(
                "spot_price_limit"
            )

            max_power = data.get(
                "max_power"
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

        except Exception as exc:
            print(
                f"Heater control config load error: "
                f"{exc}"
            )

    # ========================================================
    # SAVE
    # ========================================================

    def _save(self):

        data = {
            "mode": self.mode,

            "spot_price_limit": (
                self.spot_price_limit
            ),

            "max_power": (
                self.max_power
            ),
        }

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

                "controller_power": (
                    self.controller_power
                ),

                "controller_reason": (
                    self.controller_reason
                ),

                "controller_timestamp": (
                    self.controller_timestamp
                ),
            }

    # ========================================================
    # UPDATE
    # ========================================================

    def update(
        self,
        mode=None,
        spot_price_limit=None,
        max_power=None,
    ):

        with self._lock:

            if mode is not None:

                if mode not in self.ALLOWED_MODES:
                    raise ValueError(
                        "Invalid heater mode"
                    )

                self.mode = mode

            if spot_price_limit is not None:

                value = float(
                    spot_price_limit
                )

                if not (
                    -100.0
                    <= value
                    <= 500.0
                ):
                    raise ValueError(
                        "Invalid spot price limit"
                    )

                self.spot_price_limit = value

            if max_power is not None:

                value = int(
                    max_power
                )

                if not (
                    self.MIN_POWER
                    <= value
                    <= self.MAX_POWER
                ):
                    raise ValueError(
                        "Invalid heater max power"
                    )

                self.max_power = value

            self._save()

            return {
                "mode": self.mode,

                "spot_price_limit": (
                    self.spot_price_limit
                ),

                "max_power": (
                    self.max_power
                ),
            }

    def update_controller_status(
        self,
        power,
        reason,
    ):

        with self._lock:

            self.controller_power = int(
                power
            )

            self.controller_reason = str(
                reason
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

                "controller_timestamp": (
                    self.controller_timestamp
                ),
            }
