import json
import os
import threading
import time
import requests
from datetime import datetime, timezone



class SpotPriceService:
    API_URL = "https://api.porssisahko.net/v2/latest-prices.json"

    def __init__(
        self,
        cache_file="spot_prices.json",
        fetch_hour=17,
        retry_interval=900,
    ):
        self.cache_file = cache_file
        self.fetch_hour = fetch_hour
        self.retry_interval = retry_interval

        self.prices = []
        self.last_update = None
        self.error = None

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._last_fetch_date = None

        self._load_cache()

    # ========================================================
    # ISO 8601 UTC
    # ========================================================

    @staticmethod
    def _parse_time(value):
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    # ========================================================
    # CACHE
    # ========================================================

    def _load_cache(self):
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(
                self.cache_file,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

            prices = data.get("prices", [])
            last_update = data.get("last_update")

            if isinstance(prices, list):
                with self._lock:
                    self.prices = prices
                    self.last_update = last_update

        except Exception as exc:
            with self._lock:
                self.error = (
                    f"Cache load failed: {exc}"
                )

    def _save_cache(self):
        data = {
            "last_update": self.last_update,
            "prices": self.prices,
        }

        temp_file = (
            self.cache_file
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
            self.cache_file
        )

    # ========================================================
    # FETCH
    # ========================================================

    def fetch_prices(self):

        response = requests.get(
            self.API_URL,
            headers={
                "User-Agent": "curl/8.5.0",
                "Accept": "application/json",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        prices = data.get(
            "prices"
        )

        if not isinstance(
            prices,
            list
        ):
            raise ValueError(
                "API-vastauksesta puuttuu prices"
            )

        if not prices:
            raise ValueError(
                "API palautti tyhjän hintalistan"
            )

        # Tarkistetaan että rakenne näyttää oikealta.
        for item in prices:
            if (
                "price" not in item
                or "startDate" not in item
                or "endDate" not in item
            ):
                raise ValueError(
                    "Virheellinen hintatieto API:ssa"
                )

        now = time.time()

        with self._lock:
            self.prices = prices
            self.last_update = now
            self.error = None

            self._save_cache()

        return len(
            prices
        )

    # ========================================================
    # CURRENT PRICE
    # ========================================================

    def get_current_price(self):
        now = datetime.now(
            timezone.utc
        )

        with self._lock:
            prices = list(
                self.prices
            )

        for item in prices:
            try:
                start = self._parse_time(
                    item["startDate"]
                )

                end = self._parse_time(
                    item["endDate"]
                )

                if (
                    start
                    <= now
                    <= end
                ):
                    return {
                        "price": float(
                            item["price"]
                        ),
                        "start": item[
                            "startDate"
                        ],
                        "end": item[
                            "endDate"
                        ],
                    }

            except Exception:
                continue

        return None

    # ========================================================
    # STATUS
    # ========================================================

    def get_status(self):
        current = (
            self.get_current_price()
        )

        with self._lock:
            last_update = (
                self.last_update
            )

            error = (
                self.error
            )

            price_count = len(
                self.prices
            )

        if current is None:
            return {
                "current": None,
                "unit": "c/kWh",
                "vat_included": True,
                "start": None,
                "end": None,
                "last_update": last_update,
                "price_count": price_count,
                "error": (
                    error
                    or "Current price not found"
                ),
            }

        return {
            "current": current[
                "price"
            ],
            "unit": "c/kWh",
            "vat_included": True,
            "start": current[
                "start"
            ],
            "end": current[
                "end"
            ],
            "last_update": last_update,
            "price_count": price_count,
            "error": error,
        }

    # ========================================================
    # BACKGROUND LOOP
    # ========================================================

    def _run(self):
        # Käynnistyksessä haetaan heti.
        try:
            self.fetch_prices()

            local_now = datetime.now()
            self._last_fetch_date = (
                local_now.date()
            )

        except Exception as exc:
            with self._lock:
                self.error = str(
                    exc
                )

        while not self._stop_event.is_set():
            now = datetime.now()

            should_fetch = (
                now.hour
                >= self.fetch_hour
                and (
                    self._last_fetch_date
                    != now.date()
                )
            )

            if should_fetch:
                try:
                    self.fetch_prices()

                    self._last_fetch_date = (
                        now.date()
                    )

                except Exception as exc:
                    with self._lock:
                        self.error = str(
                            exc
                        )

            self._stop_event.wait(
                self.retry_interval
            )

    # ========================================================
    # START / STOP
    # ========================================================

    def start(self):
        if (
            self._thread
            and self._thread.is_alive()
        ):
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="SpotPriceService",
            daemon=True,
        )

        self._thread.start()

    def stop(self):
        self._stop_event.set()

        if self._thread:
            self._thread.join(
                timeout=2
            )
