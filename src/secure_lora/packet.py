import struct
from .constants import *

PACKET_HEADER_FMT = "!B I B I"
# Version (1), SenderID (4), MsgType (1), Counter (4)

class Packet:
    def __init__(self, version, sender_id, msg_type, counter, payload, hmac):
        self.version = version
        self.sender_id = sender_id
        self.msg_type = msg_type
        self.counter = counter
        self.payload = payload
        self.hmac = hmac

    def serialize_without_hmac(self):
        return (
            struct.pack(
                PACKET_HEADER_FMT,
                self.version,
                self.sender_id,
                self.msg_type,
                self.counter
            ) + self.payload
        )

    def serialize(self):
        return self.serialize_without_hmac() + self.hmac

    @staticmethod
    def parse(data: bytes):
        header_size = struct.calcsize(PACKET_HEADER_FMT)
        header = data[:header_size]
        payload_and_hmac = data[header_size:]

        version, sender_id, msg_type, counter = struct.unpack(
            PACKET_HEADER_FMT, header
        )

        payload = payload_and_hmac[:-HMAC_SIZE]
        hmac = payload_and_hmac[-HMAC_SIZE:]

        return Packet(
            version,
            sender_id,
            msg_type,
            counter,
            payload,
            hmac
        )
