from pymodbus.client import ModbusTcpClient


class SMAInverter:

    def __init__(self, name, ip, unit_id=3):
        self.name = name
        self.ip = ip
        self.unit_id = unit_id

    def test_connection(self):

        print(f"\nConnecting to {self.name} ({self.ip})...")

        client = ModbusTcpClient(
            host=self.ip,
            port=502,
            timeout=3
        )

        if not client.connect():
            print("  Connection failed")
            return

        print("  Connected")

        try:
            result = client.read_holding_registers(
                address=30000,
                count=10,
                device_id=self.unit_id
            )

            if result.isError():
                print("  Modbus error:", result)
            else:
                print("  Registers:")
                print(result.registers)

        except Exception as e:
            print("  Exception:", e)

        finally:
            client.close()


if __name__ == "__main__":
    from sma.discovery import load_devices

    devices = [
        SMAInverter(device.model, device.ip)
        for device in load_devices()
        if device.type == "inverter"
    ]

    for dev in devices:
        dev.test_connection()
