import time
import busio
from digitalio import DigitalInOut
import board
import adafruit_rfm9x
from secure_lora.radio import RadioInterface

# SPI and pins
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
CS = board.CE1
RESET = board.D25

# Initialize radio
radio = RFM95xRadio(spi, CS, RESET, freq_mhz=915.0, tx_power=5)

counter = 0

while True:
    msg = f"Hello from Pi #{counter}"
    print(f"Sending: {msg}")
    radio.send(bytes(msg, "utf-8"))

    print("Waiting for packets (5s timeout)...")
    packet = radio.receive(timeout=5.0)
    if packet:
        packet_text = packet.decode("utf-8", errors="replace")
        rssi = radio.radio.last_rssi
        print(f"Received: {packet_text}")
        print(f"Signal Strength: {rssi} dBm")
    else:
        print("No reply received.")

    counter += 1
    time.sleep(1)
