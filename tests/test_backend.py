# main.py
import os

from web_backend.server import create_app
from secure_lora.tests.dummy_network import LoopbackNetwork, DummyRadio
from secure_lora.secure_lora import SecureLoRa

from secure_lora.keystore import KeyStore
from Crypto.Random import get_random_bytes

keys = KeyStore()
keys.add_key(0xA3F91C42, get_random_bytes(16))
keys.add_key(0xB4E82D53, get_random_bytes(16))

network = LoopbackNetwork()

radio1 = DummyRadio(network)
radio2 = DummyRadio(network)

secure_lora = SecureLoRa(radio1, 0xA3F91C42, keys, debug=True)

app = create_app(secure_lora)

import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
