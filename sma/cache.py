from threading import Lock


class SMACache:

    def __init__(self):
        self._lock = Lock()

        self.data = {
            "grid": {},
            "energy_meter": {},
            "inverters": {}
        }

    def update_energy_meter(self, values):
        with self._lock:
            self.data["energy_meter"] = values

    def update_inverter(self, name, values):
        with self._lock:
            self.data["inverters"][name] = values

    def get(self):
        with self._lock:
            return self.data.copy()


cache = SMACache()
