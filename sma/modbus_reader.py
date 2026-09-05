from pymodbus.client import ModbusTcpClient


class ModbusReader:

    def __init__(self, ip, unit_id=3):
        self.ip = ip
        self.unit_id = unit_id

    def read_u32(self, address):

        client = ModbusTcpClient(
            self.ip,
            port=502,
            timeout=3
        )

        if not client.connect():
            return None

        try:

            rr = client.read_holding_registers(
                address=address,
                count=2,
                device_id=self.unit_id
            )

            if rr.isError():
                return None

            hi = rr.registers[0]
            lo = rr.registers[1]

            return (hi << 16) | lo

        finally:
            client.close()

    def read_u64(self, address):

        client = ModbusTcpClient(
            self.ip,
            port=502,
            timeout=3
        )

        if not client.connect():
            return None

        try:

            rr = client.read_holding_registers(
                address=address,
                count=4,
                device_id=self.unit_id
            )

            if rr.isError():
                return None

            r0 = rr.registers[0]
            r1 = rr.registers[1]
            r2 = rr.registers[2]
            r3 = rr.registers[3]

            return (
                (r0 << 48)
                | (r1 << 32)
                | (r2 << 16)
                | r3
            )

        finally:
            client.close()
