# main.py
import os

from web_backend.server import create_app
from secure_lora.secure_lora import SecureLoRa

from secure_lora.keystore import KeyStore
from Crypto.Random import get_random_bytes

from tests.dummy_radio import DummyRadio
import socket
import sys

import uvicorn

port = 8000
while True:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("0.0.0.0", port))
        sock.close()
        break
    except OSError:
        print(f"Port {port} is in use, trying port {port + 1}...")
        port += 1
        continue

sender_id = sys.argv[1] if len(sys.argv) > 1 else "0x01"

keys = KeyStore()
test_key = b"secure_lora_key!"
keys.add_key(0x01, test_key)
keys.add_key(0x02, test_key)

radio = DummyRadio(sender_id)

with SecureLoRa(radio, int(sender_id, 16), keys, debug=True) as secure_lora:

    app = create_app(secure_lora)
    uvicorn.run(app, host="0.0.0.0", port=port)
