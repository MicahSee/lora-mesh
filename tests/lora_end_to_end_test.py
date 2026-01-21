import time
import board
import busio
from secure_lora.packet import Packet
from secure_lora.secure_lora import SecureLoRa
from secure_lora.keystore import KeyStore
from secure_lora.platforms import RFM95xRadio
from secure_lora.constants import MsgType
from dotenv import load_dotenv
import os

# -----------------------------
# Key store setup
# -----------------------------
keys = KeyStore()
keys.add_key(0xA3F91C42, b"supersecretkey123")
keys.add_key(0xB4E82D53, b"anothersecretkey")

# -----------------------------
# SPI and radio setup
# -----------------------------
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
CS = board.CE1
RESET = board.D25

radio = RFM95xRadio(spi, CS, RESET, freq_mhz=915.0, tx_power=5)

# -----------------------------
# SecureLoRa instance
# -----------------------------
secure_lora = SecureLoRa(radio, int(os.environ.get("SENDER_ID"), 16), keys, debug=True)

counter = 0

try:
    while True:
        msg = f"Hello from Pi #{counter}"
        print(f"Sending: {msg}")
        secure_lora.send(MsgType.DATA, msg.encode("utf-8"))

        print("Waiting for packets (5s timeout)...")
        packet = secure_lora.receive(timeout=5.0)

        if packet:
            if packet.msg_type == MsgType.DATA.value:
                print(f"Received: {packet.get_payload_as_string()}")
            else:
                print(f"Ignored protocol packet: {packet.msg_type}")
        else:
            print("No reply received.")

        counter += 1
        time.sleep(1)

except KeyboardInterrupt:
    print("Stopping SecureLoRa...")
    secure_lora.stop()
