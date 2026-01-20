class KeyStore:
    def __init__(self):
        self.keys = {}

    def add_key(self, sender_id: int, key: bytes):
        self.keys[sender_id] = key

    def get_key(self, sender_id: int) -> bytes:
        return self.keys.get(sender_id)
