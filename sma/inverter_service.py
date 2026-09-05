
import time
import traceback

from sma.modbus_reader import ModbusReader
from sma.state import state



class InverterService:


    def __init__(self,name,ip):

        self.name = name

        self.reader = ModbusReader(ip)



    def run(self):


        while True:

          try:

            power = self.reader.read_u32(30775)

            if power is None:
                time.sleep(5)
                continue

            if power > 15000:
               print(f"WARNING: {self.name} Invalid power reading: {power} W")
               time.sleep(5)
               continue

            total_yield = self.reader.read_u64(30513)

            day_yield = self.reader.read_u64(30517)

            if power is None:
                print(f"{self.name}: power read failed")
                time.sleep(5)
                continue

            if total_yield is None:
                print(f"{self.name}: total_yield read failed")
                time.sleep(5)
                continue

            if day_yield is None:
                print(f"{self.name}: day_yield read failed")
                time.sleep(5)
                continue

            state.update_inverter(
                self.name,
                {
                     "power": power,
                     "total_yield": total_yield,
                     "day_yield": day_yield
                }
            )

          except Exception as e:
            print(f"InverterService ({self.name}): {e}")
            traceback.print_exc()

          time.sleep(5)
