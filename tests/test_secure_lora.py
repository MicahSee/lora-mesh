from secure_lora.packet import Packet
from secure_lora.secure_lora import SecureLoRa
from secure_lora.keystore import KeyStore
from secure_lora.radio import RadioInterface

from tests.dummy_radio import DummyRadio
import time

from Crypto.Random import get_random_bytes

# -------------------------------
# Setup keys and radios
# -------------------------------
keys = KeyStore()
keys.add_key(0xA3F91C42, get_random_bytes(16))
keys.add_key(0xB4E82D53, get_random_bytes(16))

radio1 = DummyRadio(str(0xA3F91C42))
radio2 = DummyRadio(str(0xB4E82D53))

# Use context managers to ensure threads stop automatically
with SecureLoRa(radio1, 0xA3F91C42, keys, debug=True) as lora1, \
     SecureLoRa(radio2, 0xB4E82D53, keys, debug=True) as lora2:

    # -------------------------------
    # Test 1: Basic secure message
    # -------------------------------
    message = b"Secure Hello LoRa"
    lora1.send(1, message)

    # Allow background threads a tiny moment to process
    time.sleep(0.1)

    received_packet = lora2.receive(timeout=1.0)

    assert received_packet is not None, "lora2 did not receive any packet"
    assert received_packet.payload == message, "lora2 did not receive the correct secure message"

    print("Test 1 passed: secure message received correctly")

    time.sleep(10.0)  # Wait to allow discovery to occur

    # -------------------------------
    # Test 2: Discovery handling
    # -------------------------------
    # Send discovery from lora1
    # lora1.send_discovery()

    # # Give threads time to process discovery
    # time.sleep(0.1)

    # # Discovery packets are handled internally, lora2 should not see them in receive()
    # pkt = lora2.receive(timeout=0.2)
    # assert pkt is None, "Discovery packets should not be delivered to application receive()"

    # # Check that the sender was marked seen
    # assert 0xA3F91C42 in keys._seen_nodes, "Discovery sender not recorded"

    # print("Test 2 passed: discovery handled in background correctly")