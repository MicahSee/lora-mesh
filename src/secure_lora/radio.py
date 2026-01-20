class RadioInterface:
    def send(self, data: bytes):
        raise NotImplementedError

    def receive(self) -> bytes | None:
        raise NotImplementedError
