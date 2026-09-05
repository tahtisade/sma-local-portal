import socket
import struct


MULTICAST_GROUP = "239.12.255.254"
PORT = 9522


def listen():

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


    # Liity SMA multicast-ryhmään
    mreq = struct.pack(
        "4sl",
        socket.inet_aton(MULTICAST_GROUP),
        socket.INADDR_ANY
    )


    sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_ADD_MEMBERSHIP,
        mreq
    )


    print("Listening SMA Speedwire multicast...")


    devices = {}


    while True:

        data, addr = sock.recvfrom(2048)

        ip = addr[0]


        if ip not in devices:

            devices[ip] = True

            print()
            print("NEW DEVICE")
            print("IP:", ip)


        print(
            "SIZE:",
            len(data)
        )


        print(
            data[:40].hex()
        )



if __name__ == "__main__":

    listen()
