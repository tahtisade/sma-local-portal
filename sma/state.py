from threading import Lock
from copy import deepcopy

from sma.storage import load


class SMAState:

    def __init__(self):

        self.lock = Lock()

        self.data = load()

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

        self.data["summary"] = {

            "pv_power": round(pv, 1),

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
