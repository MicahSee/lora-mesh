import time
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
import adafruit_rfm9x

# 1. Setup Pins based on our wiring
CS = DigitalInOut(board.CE1)
RESET = DigitalInOut(board.D25)
# Frequency must match your hardware (915.0, 868.0, or 433.0)
RADIO_FREQ_MHZ = 915.0 

# 2. Initialize SPI bus and Radio
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

try:
    rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
    rfm9x.reset()

    print(f"RFM9x detected! Running at {RADIO_FREQ_MHZ} MHz")
except Exception as e:
    print(f"Failed to find RFM9x: {e}")
    exit()

# 3. Increase signal strength (5 to 23 dBm)
rfm9x.tx_power = 5

print("-" * 30)
print("Instructions:")
print("Press Ctrl+C to stop.")
print("The Pi will send a message, then wait 5 seconds for a reply.")
print("-" * 30)

counter = 0

while True:
    # --- SENDING ---
    msg = f"Hello from Pi #{counter}"
    print(f"Sending: {msg}")
    rfm9x.send(bytes(msg, "utf-8"))
    
    # --- RECEIVING ---
    print("Waiting for packets (5s timeout)...")
    packet = rfm9x.receive(timeout=5.0) # Wait up to 5 seconds
    
    if packet is not None:
        packet_text = str(packet, "utf-8", errors="replace")
        rssi = rfm9x.last_rssi
        print(f"Received: {packet_text}")
        print(f"Signal Strength: {rssi} dBm")
    else:
        print("No reply received.")

    counter += 1
    time.sleep(1) # Small delay before next loop
