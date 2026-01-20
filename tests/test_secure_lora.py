from secure_lora.packet import Packet
from secure_lora.secure_lora import SecureLoRa
from secure_lora.keystore import KeyStore
from secure_lora.radio import RadioInterface

from dummy_network import LoopbackNetwork, DummyRadio

keys = KeyStore()
keys.add_key(0xA3F91C42, b"supersecretkey123")
keys.add_key(0xB4E82D53, b"anothersecretkey")

network = LoopbackNetwork()
radio1 = DummyRadio(network)
lora = SecureLoRa(radio1, 0xA3F91C42, keys)

radio2 = DummyRadio(network)
lora2 = SecureLoRa(radio2, 0xB4E82D53, keys)

def test_secure_lora_communication():
    message = b"Secure Hello LoRa"

    # lora sends a secure message to lora2
    lora.send(1, message)

    # lora2 receives the message
    received_packet = lora2.receive()

    assert received_packet.payload == message, "lora2 did not receive the correct secure message"