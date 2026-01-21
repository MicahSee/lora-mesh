from enum import Enum, IntEnum

PROTOCOL_VERSION = 1

SENDER_ID_SIZE = 4
COUNTER_SIZE = 4
MSG_TYPE_SIZE = 1

HMAC_SIZE = 8  # truncated HMAC-SHA256 (64-bit)

MAX_PAYLOAD_SIZE = 128

class MsgType(IntEnum):
    DATA = 1
    ACK = 2
    COMMAND = 3
    RESPONSE = 4
    DISCOVERY = 5