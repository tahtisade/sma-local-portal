import socket
import struct
import time

from sma.inverter_parser import parse_inverter

MULTICAST = "239.12.255.254"
PORT = 9522


class SMAInverter:


    def __init__(self, name, model, ip):

        self.name = name
        self.model = model
        self.ip = ip

        self.last_packet = None
        self.last_update = None



    def listen(self):

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


        sock.bind(
            ("", PORT)
        )


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


        print(
            "SMA Inverter listener started"
        )


        while True:


            data, addr = sock.recvfrom(2048)


            source = addr[0]


            if source == self.ip:


                self.last_packet = data

                self.last_update = time.time()


                print()
                print(
                    "INVERTER:",
                    self.name
                )

                print(
                    "MODEL:",
                    self.model
                )

                print(
                    "IP:",
                    source
                )

                print(
                    "SIZE:",
                    len(data)
                )

                parse_inverter(
                data,
                addr[0]
               )



if __name__ == "__main__":
    from sma.discovery import load_devices

    inverters = [
        SMAInverter(
            device.name,
            device.model,
            device.ip
        )
        for device in load_devices()
        if device.type == "inverter"
    ]


    # kuunnellaan kaikkia yhtä aikaa

    ips = [
        inv.ip
        for inv in inverters
    ]


    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )


    sock.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )


    sock.bind(
        ("", PORT)
    )


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


    print("Listening inverter traffic...")


    while True:


        data, addr = sock.recvfrom(2048)


        if addr[0] in ips:


            print()
            print("INVERTER DATA")
            print("----------------")

            print(
                "IP:",
                addr[0]
            )

            print(
                "BYTES:",
                len(data)
            )

            print(
                data.hex()
            )
