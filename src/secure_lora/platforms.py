import busio
from digitalio import DigitalInOut
import board
import adafruit_rfm9x
from .radio import RadioInterface, radio_param


class RFM95xRadio(RadioInterface):
    """
    Radio interface for the Adafruit RFM95x module (based on Semtech SX1276).

    Exposes all tunable LoRa parameters for UI generation via @radio_param decorators.
    """

    # Valid bandwidth values in Hz for RFM9x
    BANDWIDTHS = [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000]

    def __init__(self, spi, cs_pin, reset_pin, freq_mhz: float = 915.0, tx_power: int = 13):
        self.cs = DigitalInOut(cs_pin)
        self.reset = DigitalInOut(reset_pin)

        try:
            self.radio = adafruit_rfm9x.RFM9x(spi, self.cs, self.reset, freq_mhz)
            self.radio.enable_crc = True
            self.radio.tx_power = tx_power
            print(f"RFM9x detected! Running at {freq_mhz} MHz with TX power {tx_power} dBm")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize RFM9x: {e}")

    def send(self, data: bytes) -> None:
        """Send bytes over the radio."""
        self.radio.send(data)

    def receive(self, timeout: float = 0.5) -> bytes | None:
        """
        Receive bytes from the radio.
        Returns None if no packet is received within the timeout.
        """
        packet = self.radio.receive(timeout=timeout)
        if packet is not None:
            print(f"RFM95x received raw data: {packet}")
        return packet

    # -------------------------------------------------------------------------
    # Tunable Parameters (exposed via @radio_param for UI generation)
    # -------------------------------------------------------------------------

    @property
    @radio_param("float", (240.0, 960.0), unit="MHz", description="Carrier frequency", step=0.1)
    def frequency(self) -> float:
        return self.radio.frequency_mhz

    @frequency.setter
    def frequency(self, value: float) -> None:
        self.radio.frequency_mhz = value

    @property
    @radio_param("int", (5, 23), unit="dBm", description="Transmit power", step=1)
    def tx_power(self) -> int:
        return self.radio.tx_power

    @tx_power.setter
    def tx_power(self, value: int) -> None:
        self.radio.tx_power = value

    @property
    @radio_param("enum", [6, 7, 8, 9, 10, 11, 12], description="Spreading factor (higher = longer range, slower)")
    def spreading_factor(self) -> int:
        return self.radio.spreading_factor

    @spreading_factor.setter
    def spreading_factor(self, value: int) -> None:
        self.radio.spreading_factor = value

    @property
    @radio_param(
        "enum",
        [7800, 10400, 15600, 20800, 31250, 41700, 62500, 125000, 250000, 500000],
        unit="Hz",
        description="Signal bandwidth (lower = longer range, slower)",
    )
    def signal_bandwidth(self) -> int:
        return self.radio.signal_bandwidth

    @signal_bandwidth.setter
    def signal_bandwidth(self, value: int) -> None:
        self.radio.signal_bandwidth = value

    @property
    @radio_param("enum", [5, 6, 7, 8], description="Coding rate denominator (4/5 to 4/8, higher = more redundancy)")
    def coding_rate(self) -> int:
        return self.radio.coding_rate

    @coding_rate.setter
    def coding_rate(self, value: int) -> None:
        self.radio.coding_rate = value

    @property
    @radio_param("int", (6, 65535), description="Preamble length in symbols", step=1)
    def preamble_length(self) -> int:
        return self.radio.preamble_length

    @preamble_length.setter
    def preamble_length(self, value: int) -> None:
        self.radio.preamble_length = value

    @property
    @radio_param("bool", [True, False], description="Enable CRC checking")
    def enable_crc(self) -> bool:
        return self.radio.enable_crc

    @enable_crc.setter
    def enable_crc(self, value: bool) -> None:
        self.radio.enable_crc = value

    @property
    @radio_param("int", (0, 255), description="Node address for filtering", step=1)
    def node(self) -> int:
        return self.radio.node

    @node.setter
    def node(self, value: int) -> None:
        self.radio.node = value

    @property
    @radio_param("int", (0, 255), description="Destination address (255 = broadcast)", step=1)
    def destination(self) -> int:
        return self.radio.destination

    @destination.setter
    def destination(self, value: int) -> None:
        self.radio.destination = value

    # -------------------------------------------------------------------------
    # Read-only Parameters (signal quality)
    # -------------------------------------------------------------------------

    @property
    @radio_param("float", (-150.0, 0.0), unit="dBm", description="Last received signal strength", readonly=True)
    def last_rssi(self) -> float:
        return self.radio.last_rssi

    @property
    @radio_param("float", (-20.0, 20.0), unit="dB", description="Last signal-to-noise ratio", readonly=True)
    def last_snr(self) -> float:
        return self.radio.last_snr
