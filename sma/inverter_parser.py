def parse_inverter(data, ip):

    print()
    print("SMA INVERTER")
    print("----------------")

    print("IP:", ip)

    print("Bytes:", len(data))


    if data[0:3] == b"SMA":

        print("Valid SMA frame")


    print()

    print("RAW:")
    print(data.hex())


    print()

    print("Fields:")

    print(
        "Header:",
        data[0:4].hex()
    )


    print(
        "Frame type:",
        data[4:8].hex()
    )


    print(
        "Device data:",
        data[8:16].hex()
    )
