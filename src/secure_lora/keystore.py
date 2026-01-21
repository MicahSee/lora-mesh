class KeyStore:
    def __init__(self):
        self.keys = {}

    def add_key(self, sender_id: int, key: bytes):
        self.keys[sender_id] = key

    def get_key(self, sender_id: int) -> bytes:
        return self.keys.get(sender_id)
    
    def has_sender(self, sender_id: int) -> bool:
        return sender_id in self.keys
