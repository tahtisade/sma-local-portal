from sma.discovery import load_devices
from sma.modbus_reader import ModbusReader


inverters = [
    device
    for device in load_devices()
    if device.type == "inverter"
]

if not inverters:
    raise RuntimeError("No inverters configured in devices.yaml")

device = inverters[0]

print(f"Testing {device.id} ({device.model})")

reader = ModbusReader(device.ip)

print("Power:", reader.read_u32(30775), "W")

total = reader.read_u64(30513)
day = reader.read_u64(30517)

print("Total Yield:", total)
print("Day Yield:", day)

if total is not None:
    print("Total Yield:", round(total / 1000, 2), "kWh")

if day is not None:
    print("Day Yield:", round(day / 1000, 2), "kWh")
