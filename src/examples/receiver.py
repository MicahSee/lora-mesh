from secure_lora.secure_lora import SecureLoRa
from secure_lora.keystore import KeyStore
from secure_lora.radio import RadioInterface

class DummyRadio(RadioInterface):
    def __init__(self, packet):
        self.packet = packet

    def send(self, data):
        pass

    def receive(self):
        return self.packet

keys = KeyStore()
keys.add_key(0xA3F91C42, b"supersecretkey123")

radio = DummyRadio(None)
lora = SecureLoRa(radio, 0xFFFFFFFF, keys)
