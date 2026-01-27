# main.py
import os
import board
import busio
from dotenv import load_dotenv

from secure_lora.keystore import KeyStore
from secure_lora.platforms import RFM95xRadio
from secure_lora.secure_lora import SecureLoRa

from web_backend.server import create_app

import uvicorn

load_dotenv()

keys = KeyStore()

if "KEYS" not in os.environ or "SENDER_ID" not in os.environ:
    raise EnvironmentError("KEYS and SENDER_ID must be set in the environment variables or defined in .env file.")

for key in os.environ["KEYS"].split(","):
    node_id, key_hex = key.split(":")
    keys.add_key(int(node_id, 16), bytes.fromhex(key_hex))

spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
radio = RFM95xRadio(spi, board.CE1, board.D25, freq_mhz=915.0, tx_power=5)

with SecureLoRa(
    radio,
    int(os.environ["SENDER_ID"], 16),
    keys,
    debug=True,
) as secure_lora:
    app = create_app(secure_lora)
    uvicorn.run(app, host="0.0.0.0", port=8000)
