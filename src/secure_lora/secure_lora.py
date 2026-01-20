from .constants import *
from .packet import Packet
from .crypto import compute_hmac, verify_hmac
from .replay import ReplayProtection
from .keystore import KeyStore

class SecureLoRa:
    def __init__(self, radio, sender_id, key_store: 'KeyStore', debug: bool = False):
        self.radio = radio
        self.sender_id = sender_id
        self.key_store = key_store
        self.counter = 0
        self.replay = ReplayProtection()
        self.debug = debug

    def send(self, msg_type: int, payload: bytes):
        self.counter += 1

        packet = Packet(
            version=PROTOCOL_VERSION,
            sender_id=self.sender_id,
            msg_type=msg_type,
            counter=self.counter,
            payload=payload,
            hmac=b""
        )

        key = self.key_store.get_key(self.sender_id)
        raw = packet.serialize_without_hmac()
        packet.hmac = compute_hmac(key, raw)

        self.radio.send(packet.serialize())

    def receive(self):
        data = self.radio.receive()
        if not data:
            return None

        packet = Packet.parse(data)

        if self.debug:
            print(f"Received packet from {hex(packet.sender_id)}:")
            print(f"  Version: {packet.version}")
            print(f"  MsgType: {packet.msg_type}")
            print(f"  Counter: {packet.counter}")
            print(f"  Payload: {packet.get_payload_as_string()}")
            print(f"  HMAC: {packet.hmac.hex()}")

        if packet.sender_id == self.sender_id:
            if self.debug:
                print("  Ignoring packet from self.")
            return None

        key = self.key_store.get_key(packet.sender_id)
        if not key:
            return None

        raw = packet.serialize_without_hmac()
        if not verify_hmac(key, raw, packet.hmac):
            return None

        if not self.replay.check_and_update(packet.sender_id, packet.counter):
            return None

        return packet
