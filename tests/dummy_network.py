from typing import Optional
from collections import deque
from secure_lora.radio import RadioInterface

class LoopbackNetwork:
    """
    Simulates a simple network connecting multiple DummyRadio instances.
    Each radio registers itself and can send data to the network.
    """
    def __init__(self):
        self._queues = {}  # radio_id -> list of messages

    def register(self, radio):
        self._queues[radio] = []

    def send(self, sender, data):
        # Deliver to all other radios except sender
        for radio in self._queues:
            if radio != sender:
                self._queues[radio].append(data)

    def receive(self, radio):
        if self._queues[radio]:
            return self._queues[radio].pop(0)
        return None


class DummyRadio:
    """
    Dummy radio that sends/receives via the LoopbackNetwork.
    """
    def __init__(self, network: LoopbackNetwork):
        self.network = network
        self.network.register(self)

    def send(self, data: bytes):
        self.network.send(self, data)

    def receive(self) -> bytes | None:
        return self.network.receive(self)
