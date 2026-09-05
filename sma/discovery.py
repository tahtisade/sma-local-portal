import yaml

from sma.devices import SMADevice


def load_devices():

    with open("devices.yaml", "r") as f:

        data = yaml.safe_load(f)


    devices = []


    for d in data["devices"]:

        device = SMADevice(
            d["name"],
            d["type"],
            d["ip"],
            d.get("model"),
            d.get("id")
        )

        devices.append(device)


    return devices



if __name__ == "__main__":

    print("SMA Local Portal")
    print("----------------")


    devices = load_devices()


    for device in devices:

        print(
            device.name,
            "-",
            device.type,
            "-",
            device.ip
        )
