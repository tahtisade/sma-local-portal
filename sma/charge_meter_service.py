import struct
import threading
import time
import json
from datetime import date
from pathlib import Path

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException


class ChargeMeterService:
    def __init__(
        self,
        port="/dev/ttyUSB0",
        device_id=1,
        baudrate=9600,
        bytesize=8,
        parity="E",
        stopbits=1,
        timeout=2,
    ):
        self.port = port
        self.device_id = device_id
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.timeout = timeout

        self.power = 0.0
        self.total_energy = 0.0
        self.daily_energy = 0.0
        self.day_date = None
        self.day_start_energy = None

        self.daily_state_file = (
            Path(__file__).resolve().parent.parent
            / "charge_meter_daily.json"
        )

        self._load_daily_state()

        self.error = None
        self.timestamp = None

        self.lock = threading.Lock()
        self.client = None

    def _connect(self):
        self.client = ModbusSerialClient(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=self.bytesize,
            parity=self.parity,
            stopbits=self.stopbits,
            timeout=self.timeout,
            retries=1,
        )


        return self.client.connect()

    def _read_power(self):
        result = self.client.read_input_registers(
            address=52,
            count=2,
            device_id=self.device_id,
        )

        if result.isError():
            raise RuntimeError(f"Modbus error: {result}")

        raw = struct.pack(
            ">HH",
            result.registers[0],
            result.registers[1],
        )

        return struct.unpack(">f", raw)[0]

    def _read_total_energy(self):
        result = self.client.read_input_registers(
            address=72,
            count=2,
            device_id=self.device_id,
        )

        if result.isError():
            raise RuntimeError(f"Modbus error: {result}")

        raw = struct.pack(
            ">HH",
            result.registers[0],
            result.registers[1],
        )

        return struct.unpack(">f", raw)[0]

    def _load_daily_state(self):
        try:
            if not self.daily_state_file.exists():
                return

            with open(self.daily_state_file, "r") as f:
                data = json.load(f)

            self.day_date = data.get("date")
            self.day_start_energy = data.get("start_energy")

        except (OSError, ValueError, TypeError):
            self.day_date = None
            self.day_start_energy = None


    def _save_daily_state(self):
        data = {
            "date": self.day_date,
            "start_energy": self.day_start_energy,
        }

        with open(self.daily_state_file, "w") as f:
            json.dump(data, f, indent=2)


    def _update_daily_energy(self, total_energy):
        today = date.today().isoformat()

        if (
            self.day_date != today
            or self.day_start_energy is None
            or total_energy < self.day_start_energy
        ):
            self.day_date = today
            self.day_start_energy = total_energy
            self._save_daily_state()

        self.daily_energy = max(
            0.0,
            total_energy - self.day_start_energy
        )

    def get(self):
        with self.lock:
            return {
                "power": round(self.power, 1),
                "total_energy": round(self.total_energy, 2),
                "daily_energy": round(self.daily_energy, 2),
                "error": self.error,
                "timestamp": self.timestamp,
            }

    def run(self):
        print("Charge meter service starting")

        while True:
            try:
                if self.client is None or not self.client.connected:
                    if not self._connect():
                        raise RuntimeError(
                            f"Could not open {self.port}"
                        )

                power = self._read_power()
                total_energy = self._read_total_energy()
                self._update_daily_energy(total_energy)

                with self.lock:
                    self.power = power
                    self.total_energy = total_energy
                    self.error = None
                    self.timestamp = time.time()

            except (ModbusException, RuntimeError, OSError) as exc:
                with self.lock:
                    self.error = str(exc)

                if self.client is not None:
                    try:
                        self.client.close()
                    except Exception:
                        pass

                self.client = None

            time.sleep(1)
