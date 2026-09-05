import struct

DEBUG = False

def parse_energy_meter(data):

    values = {}

    pos = 28

    while pos + 8 <= len(data):

        tag = struct.unpack(">H", data[pos:pos + 2])[0]
        dtype = struct.unpack(">H", data[pos + 2:pos + 4])[0]

        if dtype == 0x0400:

            value = struct.unpack(">I", data[pos + 4:pos + 8])[0]

            if DEBUG:
                print(
                    f"TAG={tag:3d} "
                    f"TYPE={hex(dtype)} "
                    f"POS={pos:3d} "
                    f"VALUE={value}"
                )

            values[f"tag_{tag}_{dtype:04x}"] = value
            pos += 8

        elif dtype == 0x0800:

            value = struct.unpack(">Q", data[pos + 4:pos + 12])[0]

            if DEBUG:
                print(
                    f"TAG={tag:3d} "
                    f"TYPE={hex(dtype)} "
                    f"POS={pos:3d} "
                    f"VALUE={value}"
                )

            values[f"tag_{tag}_{dtype:04x}"] = value
            pos += 12

        else:
            #
            # Paketin loppu / tuntematon tietotyyppi.
            # Lopetetaan parseri siististi.
            #
            if DEBUG:
                print(
                    f"Parser stopped: "
                    f"pos={pos}, "
                    f"tag={tag}, "
                    f"type={hex(dtype)}"
                )
            break

    #
    # Kokonaistehot
    #

    values["grid_import"] = values.get("tag_1_0400", 0) / 10.0
    values["grid_export"] = values.get("tag_2_0400", 0) / 10.0

    values["grid_power"] = (
        values["grid_import"]
        - values["grid_export"]
    )


    #
    # Energialaskurit (64-bit raakaarvot)
    # Skaala varmistetaan myöhemmin.
    #

    values["grid_import_counter"] = values.get("tag_1_0800", 0)
    values["grid_export_counter"] = values.get("tag_2_0800", 0)
    values["tag3_counter"] = values.get("tag_3_0800", 0)
    values["tag4_counter"] = values.get("tag_4_0800", 0)

    values["tag9_counter"] = values.get("tag_9_0800", 0)
    values["tag10_counter"] = values.get("tag_10_0800", 0)


    #
    # Vaihekohtaiset aktiivitehot
    # (tagit vielä alustavia, vaativat vahvistuksen)
    #

    values["phase1_import"] = values.get("tag_21_0400", 0) / 10.0
    values["phase2_import"] = values.get("tag_41_0400", 0) / 10.0
    values["phase3_import"] = values.get("tag_61_0400", 0) / 10.0

    values["phase1_export"] = values.get("tag_22_0400", 0) / 10.0
    values["phase2_export"] = values.get("tag_42_0400", 0) / 10.0
    values["phase3_export"] = values.get("tag_62_0400", 0) / 10.0

    #
    # Vaihekohtaiset energialaskurit
    # (tagit vielä alustavia, vaativat vahvistuksen)
    #

    values["phase1_import_counter"] = values.get("tag_21_0800", 0)
    values["phase2_import_counter"] = values.get("tag_41_0800", 0)
    values["phase3_import_counter"] = values.get("tag_61_0800", 0)

    values["phase1_export_counter"] = values.get("tag_22_0800", 0)
    values["phase2_export_counter"] = values.get("tag_42_0800", 0)
    values["phase3_export_counter"] = values.get("tag_62_0800", 0)

    #
    # Jännitteet
    #

    values["phase1_voltage"] = values.get("tag_32_0400", 0) / 1000.0
    values["phase2_voltage"] = values.get("tag_52_0400", 0) / 1000.0
    values["phase3_voltage"] = values.get("tag_72_0400", 0) / 1000.0

    #
    # Virrat
    #

    values["phase1_current"] = values.get("tag_31_0400", 0) / 1000.0
    values["phase2_current"] = values.get("tag_51_0400", 0) / 1000.0
    values["phase3_current"] = values.get("tag_71_0400", 0) / 1000.0

    #
    # Vaihekohtaiset näennäistehot (VA)
    #

    values["phase1_va_import"] = values.get("tag_29_0400", 0) / 10.0
    values["phase2_va_import"] = values.get("tag_49_0400", 0) / 10.0
    values["phase3_va_import"] = values.get("tag_69_0400", 0) / 10.0

    values["phase1_va_export"] = values.get("tag_30_0400", 0) / 10.0
    values["phase2_va_export"] = values.get("tag_50_0400", 0) / 10.0
    values["phase3_va_export"] = values.get("tag_70_0400", 0) / 10.0

    if DEBUG:
        print()
        print("==============================")
        print("ENERGY METER")
        print("==============================")
        print(f"Grid import : {values['grid_import']:.1f} W")
        print(f"Grid export : {values['grid_export']:.1f} W")
        print(f"Grid net    : {values['grid_power']:.1f} W")
        print()


    return values
