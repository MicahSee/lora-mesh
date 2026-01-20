import hmac
import hashlib
from .constants import HMAC_SIZE

def compute_hmac(key: bytes, data: bytes) -> bytes:
    digest = hmac.new(key, data, hashlib.sha256).digest()
    return digest[:HMAC_SIZE]

def verify_hmac(key: bytes, data: bytes, received_hmac: bytes) -> bool:
    expected = compute_hmac(key, data)
    return hmac.compare_digest(expected, received_hmac)
