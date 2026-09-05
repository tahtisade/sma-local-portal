import json
import threading
import time
import urllib.request


class ResolService:
    def __init__(
        self,
        url,
        header_index=1,
        field_index=11,
        poll_interval=10,
    ):
        self.url = url
        self.header_index = header_index
        self.field_index = field_index
        self.poll_interval = poll_interval

        self.temperature = None
        self.timestamp = None
        self.error = None

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

    def _read_temperature(self):
        with urllib.request.urlopen(self.url, timeout=5) as response:
            data = json.load(response)

        for headerset in data.get("headersets", []):
            for packet in headerset.get("packets", []):
                if packet.get("header_index") != self.header_index:
                    continue

                for field in packet.get("field_values", []):
                    if field.get("field_index") == self.field_index:
                        value = field.get("raw_value")

                        if value is None:
                            return None

                        return float(value)

        return None

    def _run(self):
        while not self._stop_event.is_set():
            try:
                temperature = self._read_temperature()

                if temperature is None:
                    raise ValueError("RESOL temperature field not found")

                with self._lock:
                    self.temperature = temperature
                    self.timestamp = time.time()
                    self.error = None

            except Exception as exc:
                with self._lock:
                    self.error = str(exc)

            self._stop_event.wait(self.poll_interval)

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            name="ResolService",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=2)

    def get_status(self):
        with self._lock:
            return {
                "LKV 500l": self.temperature,
                "timestamp": self.timestamp,
                "error": self.error,
            }
