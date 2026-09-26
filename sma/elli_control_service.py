import json
import os
import threading
from datetime import datetime


class ElliControlService:

    ALLOWED_MODES = {
        "off",
        "pv",
        "price",
        "now",
    }

    def __init__(
        self,
        config_file="elli_control.json",
        default_mode="off",
        default_spot_price_limit=10.0,
        default_price_start="00:00",
        default_price_end="06:00",
    ):
        self.config_file = config_file
        self._lock = threading.Lock()

        self.mode = default_mode
        self.spot_price_limit = (
            default_spot_price_limit
        )
        self.price_start = default_price_start
        self.price_end = default_price_end

        self.controller_reason = "UNKNOWN"
        self.controller_evcc_mode = "unknown"
        self.controller_timestamp = None

        self._load()

    # ========================================================
    # TIME VALIDATION
    # ========================================================

    @staticmethod
    def _validate_time(value):

        if not isinstance(value, str):
            raise ValueError(
                "Invalid Elli price time"
            )

        try:
            parsed = datetime.strptime(
                value,
                "%H:%M"
            )

        except ValueError as exc:
            raise ValueError(
                "Invalid Elli price time"
            ) from exc

        return parsed.strftime("%H:%M")

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
                f"Elli control config load error: "
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
            "price_start": (
                self.price_start
            ),
            "price_end": (
                self.price_end
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
                "price_start": (
                    self.price_start
                ),
                "price_end": (
                    self.price_end
                ),
                "controller_reason": (
                    self.controller_reason
                ),
                "controller_evcc_mode": (
                    self.controller_evcc_mode
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
        price_start=None,
        price_end=None,
    ):

        with self._lock:

            if mode is not None:

                if mode not in self.ALLOWED_MODES:
                    raise ValueError(
                        "Invalid Elli mode"
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

            self._save()

            return {
                "mode": self.mode,
                "spot_price_limit": (
                    self.spot_price_limit
                ),
                "price_start": (
                    self.price_start
                ),
                "price_end": (
                    self.price_end
                ),
            }

    # ========================================================
    # PRICE DECISION
    # ========================================================

    def get_price_decision(
        self,
        spot_price,
        current_time=None,
    ):

        if current_time is None:
            current_time = datetime.now()

        with self._lock:

            start_hour, start_minute = (
                int(value)
                for value
                in self.price_start.split(":")
            )

            end_hour, end_minute = (
                int(value)
                for value
                in self.price_end.split(":")
            )

            start_minutes = (
                start_hour * 60
                + start_minute
            )

            end_minutes = (
                end_hour * 60
                + end_minute
            )

            current_minutes = (
                current_time.hour * 60
                + current_time.minute
            )

            if start_minutes == end_minutes:
                time_active = True

            elif start_minutes < end_minutes:
                time_active = (
                    start_minutes
                    <= current_minutes
                    < end_minutes
                )

            else:
                time_active = (
                    current_minutes
                    >= start_minutes
                    or current_minutes
                    < end_minutes
                )

            if not time_active:
                return {
                    "evcc_mode": "off",
                    "reason": "PRICE_TIME",
                }

            if spot_price is None:
                return {
                    "evcc_mode": "off",
                    "reason": "SPOT_INVALID",
                }

            try:
                price = float(
                    spot_price
                )
            except (
                TypeError,
                ValueError
            ):
                return {
                    "evcc_mode": "off",
                    "reason": "SPOT_INVALID",
                }

            if price > self.spot_price_limit:
                return {
                    "evcc_mode": "off",
                    "reason": "SPOT_HIGH",
                }

            return {
                "evcc_mode": "now",
                "reason": "PRICE_ON",
            }

    # ========================================================
    # CONTROLLER STATUS
    # ========================================================

    def update_controller_status(
        self,
        evcc_mode,
        reason,
    ):

        with self._lock:

            self.controller_evcc_mode = str(
                evcc_mode
            )

            self.controller_reason = str(
                reason
            )

            import time

            self.controller_timestamp = (
                time.time()
            )

            return {
                "controller_evcc_mode": (
                    self.controller_evcc_mode
                ),
                "controller_reason": (
                    self.controller_reason
                ),
                "controller_timestamp": (
                    self.controller_timestamp
                ),
            }
