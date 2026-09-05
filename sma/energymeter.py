import socket
import struct
import time
import traceback

from sma.parser import parse_energy_meter
from sma.state import state


MULTICAST = "239.12.255.254"
PORT = 9522

DEBUG = False


class EnergyMeter:

    def __init__(self):

        self.last_packet = None
        self.last_update = None
        self.source = None
        self.values = {}

    def start(self):

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
            socket.IPPROTO_UDP
        )

        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        sock.bind(("", PORT))

        group = struct.pack(
            "4sl",
            socket.inet_aton(MULTICAST),
            socket.INADDR_ANY
        )

        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            group
        )

        print("Energy Meter listener started")

        while True:
         try:
            data, addr = sock.recvfrom(2048)

            if len(data) < 600:
                continue

            self.source = addr[0]
            self.last_packet = data
            self.last_update = time.time()

            raw = parse_energy_meter(data)

            #
            # Lasketaan vaihekohtainen näennäisteho (VA).
            # Tämä EI ole aktiiviteho (W).
            #

            phase1_power = (
                raw.get("phase1_voltage", 0)
                * raw.get("phase1_current", 0)
            )

            phase2_power = (
                raw.get("phase2_voltage", 0)
                * raw.get("phase2_current", 0)
            )

            phase3_power = (
                raw.get("phase3_voltage", 0)
                * raw.get("phase3_current", 0)
            )

            if "grid_import_counter" not in raw or "grid_export_counter" not in raw:
                print("WARNING: Energy Meter packet missing counters!")
                print(sorted(raw.keys()))

            self.values = {

                "source": self.source,
                "timestamp": self.last_update,

                "grid_import": raw.get("grid_import", 0),
                "grid_export": raw.get("grid_export", 0),
                "grid_power": raw.get("grid_power", 0),

                "grid_import_counter": raw.get("grid_import_counter", 0),
                "grid_export_counter": raw.get("grid_export_counter", 0),

                "tag3_counter": raw.get("tag3_counter", 0),
                "tag4_counter": raw.get("tag4_counter", 0),
                "tag9_counter": raw.get("tag9_counter", 0),
                "tag10_counter": raw.get("tag10_counter", 0),

                "phase1_import_counter": raw.get("phase1_import_counter", 0),
                "phase2_import_counter": raw.get("phase2_import_counter", 0),
                "phase3_import_counter": raw.get("phase3_import_counter", 0),

                "phase1_export_counter": raw.get("phase1_export_counter", 0),
                "phase2_export_counter": raw.get("phase2_export_counter", 0),
                "phase3_export_counter": raw.get("phase3_export_counter", 0),

                "phase1_voltage": raw.get("phase1_voltage", 0),
                "phase2_voltage": raw.get("phase2_voltage", 0),
                "phase3_voltage": raw.get("phase3_voltage", 0),

                "phase1_current": raw.get("phase1_current", 0),
                "phase2_current": raw.get("phase2_current", 0),
                "phase3_current": raw.get("phase3_current", 0),

                "phase1_power": round(phase1_power, 1),
                "phase2_power": round(phase2_power, 1),
                "phase3_power": round(phase3_power, 1),

                "total_power": round(
                    phase1_power
                    + phase2_power
                    + phase3_power,
                    1
                )
            }

            state.update_energy_meter(self.values)

         except Exception as e:
            print(f"EnergyMeter: {e}")
            traceback.print_exc()

            if DEBUG:

                print()
                print("==============================")
                print("Energy Meter")
                print("==============================")

                print("IP:", self.source)
                print("Bytes:", len(data))

                for name, value in self.values.items():
                    print(f"{name}: {value}")

                print()
                print("RAW PARSER VALUES")

                for key in sorted(raw.keys()):
                    print(f"{key:20} {raw[key]}")

                print()
                print("RAW ACTIVE CANDIDATES")

                for key in (
                    "tag_13_0400",
                    "tag_21_0400",
                    "tag_29_0400",
                    "tag_41_0400",
                    "tag_49_0400",
                    "tag_61_0400",
                    "tag_69_0400",
                ):
                    if key in raw:
                        print(f"{key:20} {raw[key]}")


if __name__ == "__main__":

    meter = EnergyMeter()
    meter.start()
