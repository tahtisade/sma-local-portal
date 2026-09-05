import socket
import time


PORT = 9522


class SMARequest:


    def __init__(self, ip):

        self.ip = ip



    def send(self):

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        sock.settimeout(3)


        # SMA discovery request pohja
        packet = bytes.fromhex(
            "534d4100000402a000000001000c001060810001"
        )


        print(
            "Sending request to",
            self.ip
        )


        sock.sendto(
            packet,
            (
                self.ip,
                PORT
            )
        )


        try:

            data, addr = sock.recvfrom(2048)

            print(
                "Response:",
                addr
            )

            print(
                "Length:",
                len(data)
            )

            print(
                data.hex()
            )


        except socket.timeout:

            print(
                "No response"
            )


        sock.close()



if __name__ == "__main__":
    from sma.discovery import load_devices

    devices = [
        device.ip
        for device in load_devices()
        if device.type == "inverter"
    ]


    for ip in devices:

        req = SMARequest(ip)

        req.send()

        time.sleep(1)
