from threading import Lock
from copy import deepcopy
import math

from sma.storage import load


class SMAState:

    def __init__(self):

        self.lock = Lock()

        self.data = load()

        # Instantaneous inverter power is not persistent state.
        # After a restart, wait for fresh Modbus readings instead of
        # presenting the last saved PV power as current production.
        for inverter in self.data.get("inverters", {}).values():
            inverter["power"] = 0
            inverter.pop("timestamp", None)

        self.update_summary()

        self.dirty = False

    def update_inverter(self, name, values):

        with self.lock:

            self.data["inverters"][name] = values

            self.update_summary()

            self.dirty = True

    def update_energy_meter(self, values):

        with self.lock:

            self.data["energy_meter"] = values

            self.update_summary()

            self.dirty = True

    def update_summary(self):

        pv = sum(
            inv.get("power") or 0
            for inv in self.data["inverters"].values()
        )

        pv_total_yield = sum(
            inv.get("total_yield") or 0
            for inv in self.data["inverters"].values()
        )

        pv_day_yield = sum(
            inv.get("day_yield") or 0
            for inv in self.data["inverters"].values()
        )




        energy = self.data.get("energy_meter", {})

        grid_import = energy.get("grid_import", 0)
        grid_export = energy.get("grid_export", 0)

        house = (
            pv
            + grid_import
            - grid_export
        )

        # A combined measurement is only as recent as its oldest input.
        inverters = list(self.data["inverters"].values())
        def valid_timestamp(value):
            return (isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) and value > 0)
        times = [inv.get("timestamp") for inv in inverters]
        pv_timestamp = (min(times) if times and all(valid_timestamp(t) for t in times)
                        else None)
        grid_timestamp = energy.get("timestamp")
        house_timestamp = (min(pv_timestamp, grid_timestamp)
                           if pv_timestamp is not None and valid_timestamp(grid_timestamp)
                           else None)

        self.data["summary"] = {

            "pv_power": round(pv, 1),
            "pv_timestamp": pv_timestamp,
            "house_load_timestamp": house_timestamp,

            "house_load": round(house, 1),

            "grid_import": round(grid_import, 1),

            "grid_export": round(grid_export, 1),

            "grid_power": round(grid_import - grid_export,1),

            "pv_total_yield": round(pv_total_yield / 1000, 2),

            "pv_day_yield": round(pv_day_yield / 1000, 2),

        }

    def get(self):

        with self.lock:
            return deepcopy(self.data)

    def is_dirty(self):

        with self.lock:
            return self.dirty

    def clear_dirty(self):

        with self.lock:
            self.dirty = False


state = SMAState()
