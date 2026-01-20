from time import time
import board
import busio
from secure_lora.packet import Packet
from secure_lora.secure_lora import SecureLoRa
from secure_lora.keystore import KeyStore
from secure_lora.radio import RadioInterface
from secure_lora.platforms import RFM95xRadio

keys = KeyStore()
keys.add_key(0xA3F91C42, b"supersecretkey123")
keys.add_key(0xB4E82D53, b"anothersecretkey")

# SPI and pins
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
CS = board.CE1
RESET = board.D25

# Initialize radio
radio = RFM95xRadio(spi, CS, RESET, freq_mhz=915.0, tx_power=5)
secure_lora = SecureLoRa(radio, 0xA3F91C42, keys)
# secure_lora = SecureLoRa(radio, 0xB4E82D53, keys)

counter = 0

while True:
    msg = f"Hello from Pi #{counter}"
    print(f"Sending: {msg}")
    secure_lora.send(1, bytes(msg, "utf-8"))

    print("Waiting for packets (5s timeout)...")
    packet = secure_lora.receive()
    
    if packet:
        print(f"Received: {packet.payload}")
    else:
        print("No reply received.")

    counter += 1
    time.sleep(1)