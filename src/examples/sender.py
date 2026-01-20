from secure_lora.secure_lora import SecureLoRa
from secure_lora.keystore import KeyStore
from secure_lora.radio import RadioInterface

class DummyRadio(RadioInterface):
    def send(self, data):
        print("TX:", data)

    def receive(self):
        return None

radio = DummyRadio()
keys = KeyStore()

SENDER_ID = 0xA3F91C42
KEY = b"supersecretkey123"

keys.add_key(SENDER_ID, KEY)

lora = SecureLoRa(radio, SENDER_ID, keys)
lora.send(1, b"Hello LoRa")
