import struct
import sys
from sma.parser import parse_energy_meter


if len(sys.argv) != 2:
    raise SystemExit(f"Usage: {sys.argv[0]} <capture.pcap>")

PCAP_FILE = sys.argv[1]


def extract_udp_payload(filename):
    with open(filename, "rb") as f:
        data = f.read()

    # PCAP global header = 24 tavua
    pos = 24

    # Ensimmäinen paketti
    packet_header = data[pos:pos + 16]
    pos += 16

    captured_length = struct.unpack("<I", packet_header[8:12])[0]

    ethernet = data[pos:pos + 14]
    pos += 14

    # IPv4 header
    ip_header_length = (data[pos] & 0x0F) * 4
    pos += ip_header_length

    # UDP header
    udp_header = data[pos:pos + 8]
    udp_length = struct.unpack(">H", udp_header[4:6])[0]

    pos += 8

    payload_length = udp_length - 8
    payload = data[pos:pos + payload_length]

    return payload


print("================================")
print("SMA 600 BYTE PACKET TEST")
print("================================")

payload = extract_udp_payload(PCAP_FILE)

print(f"UDP payload length: {len(payload)} bytes")
print()

values = parse_energy_meter(payload)

print()
print("================================")
print("PARSED VALUES")
print("================================")

for key, value in values.items():
    print(f"{key:30} = {value}")
