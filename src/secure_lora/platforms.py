import time
import busio
from digitalio import DigitalInOut
import board
import adafruit_rfm9x
from .radio import RadioInterface

class RFM95xRadio(RadioInterface):
    """Radio interface for the Adafruit RFM95x module."""
    def __init__(self, spi, cs_pin, reset_pin, freq_mhz=915.0, tx_power=5):
        self.cs = DigitalInOut(cs_pin)
        self.reset = DigitalInOut(reset_pin)

        try:
            self.radio = adafruit_rfm9x.RFM9x(spi, self.cs, self.reset, freq_mhz)
            # self.radio.reset()
            self.radio.enable_crc = True
            self.radio.tx_power = tx_power
            print(f"RFM9x detected! Running at {freq_mhz} MHz with TX power {tx_power} dBm")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize RFM9x: {e}")

    def send(self, data: bytes):
        """Send bytes over the radio."""
        self.radio.send(data)

    def receive(self, timeout: float = 5.0) -> bytes | None:
        """
        Receive bytes from the radio.
        Returns None if no packet is received within the timeout.
        """
        packet = self.radio.receive(timeout=timeout)
        return packet