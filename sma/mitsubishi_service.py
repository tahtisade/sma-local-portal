import json
import threading
import time
import urllib.request


class MitsubishiService:
    """
    Read-only Mitsubishi FTC2 monitoring through
    Shelly Dimmer 0/1-10V PM Gen3.

    Shelly is polled in a background thread. get_status()
    only returns the latest cached result and never performs
    network I/O.

    The service does not change the Shelly output.
    """

    def __init__(
        self,
        shelly_url,
        temp_min=5.0,
        temp_max=60.0,
        timeout=3.0,
        poll_interval=5.0,
    ):
        self.shelly_url = shelly_url.rstrip("/")
        self.temp_min = float(temp_min)
        self.temp_max = float(temp_max)
        self.timeout = float(timeout)
        self.poll_interval = float(poll_interval)

        self._lock = threading.Lock()
        self._thread = None
        self._running = False

        self._status = self._offline_status(
            "Waiting for first Shelly poll"
        )

    def _offline_status(self, error):
        return {
            "online": False,
            "timestamp": None,
            "output": None,
            "brightness": None,
            "estimated_voltage": None,
            "requested_temperature": None,
            "device_temperature": None,
            "error": str(error),
        }

    def _get_shelly_status(self):
        url = f"{self.shelly_url}/rpc/Shelly.GetStatus"

        with urllib.request.urlopen(
            url,
            timeout=self.timeout,
        ) as response:
            return json.load(response)

    def _read_status(self):
        try:
            status = self._get_shelly_status()

            light = status.get("light:0", {})
            brightness = light.get("brightness")
            output = light.get("output")

            device_temperature = None
            temperature = light.get("temperature")

            if isinstance(temperature, dict):
                device_temperature = temperature.get("tC")

            if brightness is None:
                raise ValueError(
                    "Shelly brightness not available"
                )

            brightness = float(brightness)

            # Shelly range_map is currently 0...100 %,
            # corresponding approximately to 0...10 V.
            estimated_voltage = brightness / 10.0

            # FTC2 analog scaling:
            # 0 V = temp_min
            # 10 V = temp_max
            requested_temperature = (
                self.temp_min
                + (self.temp_max - self.temp_min)
                * estimated_voltage
                / 10.0
            )

            return {
                "online": True,
                "timestamp": time.time(),
                "output": bool(output),
                "brightness": brightness,
                "estimated_voltage": round(
                    estimated_voltage,
                    2,
                ),
                "requested_temperature": round(
                    requested_temperature,
                    1,
                ),
                "device_temperature": device_temperature,
                "error": None,
            }

        except Exception as exc:
            return self._offline_status(exc)

    def _run(self):
        while self._running:
            status = self._read_status()

            with self._lock:
                self._status = status

            # Sleep in small steps so stop() does not have to
            # wait for the full polling interval.
            deadline = time.monotonic() + self.poll_interval

            while self._running and time.monotonic() < deadline:
                time.sleep(0.2)

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._running = True

        self._thread = threading.Thread(
            target=self._run,
            name="mitsubishi-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False

        if self._thread:
            self._thread.join(
                timeout=self.timeout + 1.0
            )

    def get_status(self):
        with self._lock:
            return dict(self._status)
