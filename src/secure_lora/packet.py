import struct
from .constants import *

# Header format: Version (1) | SenderID (4) | MsgType (1) | Nonce (12)
PACKET_HEADER_FMT = "!B I B 12s"  # 1 + 4 + 1 + 4 + 12 = 22 bytes

class Packet:
    def __init__(self, version, sender_id, msg_type, payload, auth_tag, nonce):
        self.version = version
        self.sender_id = sender_id
        self.msg_type = msg_type
        self.payload = payload        # AES-GCM ciphertext
        self.auth_tag = auth_tag      # AES-GCM auth tag
        self.nonce = nonce            # 12-byte nonce

    def serialize_without_auth_tag(self):
        # Header + ciphertext
        return struct.pack(
            PACKET_HEADER_FMT,
            self.version,
            self.sender_id,
            self.msg_type,
            self.nonce
        ) + self.payload

    def serialize(self):
        # Header + ciphertext + auth tag
        return self.serialize_without_auth_tag() + self.auth_tag

    @staticmethod
    def parse(data: bytes):
        header_size = struct.calcsize(PACKET_HEADER_FMT)
        header = data[:header_size]
        payload_and_hmac = data[header_size:]

        version, sender_id, msg_type, nonce = struct.unpack(
            PACKET_HEADER_FMT, header
        )

        # AES-GCM auth tag length (16 bytes standard)
        auth_tag_size = 16
        payload = payload_and_hmac[:-auth_tag_size]
        auth_tag = payload_and_hmac[-auth_tag_size:]

        return Packet(
            version,
            sender_id,
            msg_type,
            payload,
            auth_tag,
            nonce
        )

    def get_payload_as_string(self) -> str:
        return self.payload.decode('utf-8', errors='replace')
