import board
import busio
import digitalio
import adafruit_rfm9x

# Define the pins based on our wiring table
CS = digitalio.DigitalInOut(board.CE1)
RESET = digitalio.DigitalInOut(board.D25)
# DIO0 is used for interrupts; we define it but don't need it for a simple check
LED = digitalio.DigitalInOut(board.D13) # Optional: onboard LED if available

# Initialize SPI bus
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

print("Attempting to connect to RFM9x...")

try:
    # Attempt to initialize the RFM9x radio
    # The frequency must match your hardware (e.g., 915.0 or 433.0)
    rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 915.0)
    
    # If we reach this point, the radio was found!
    print("Success!")

except Exception as e:
    print("\n--- Failed to connect! ---")
    print(f"Error: {e}")
