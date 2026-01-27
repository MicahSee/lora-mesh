import asyncio
from typing import List, Optional
from collections import deque
from dataclasses import dataclass

# Dummy MsgType Enum
class MsgType:
    DATA = 1
    CONTROL = 2

# Dummy Packet class
@dataclass
class Packet:
    version: int
    sender_id: str
    msg_type: int
    counter: int
    payload: bytes
    hmac: Optional[bytes] = None

    def get_payload_as_string(self) -> str:
        return self.payload.decode("utf-8", errors="replace")

# Dummy Secure LoRa class
class DummySecureLoRa:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._counter = 0
        self._peers = ["raspberry-pi-001", "raspberry-pi-002", "raspberry-pi-003"]
        self._incoming_packets = deque()  # Queue for received packets

    def send(self, msg_type: int, payload: bytes):
        """Simulate sending a message"""
        self._counter += 1
        msg_str = payload.decode("utf-8", errors="replace")
        print(f"[DummySecureLoRa] Sending msg #{self._counter} | type={msg_type}: {msg_str}")

        # For testing, echo back to the node itself after a short delay
        # Simulate network latency with asyncio
        packet = Packet(
            version=1,
            sender_id=self.node_id,
            msg_type=msg_type,
            counter=self._counter,
            payload=payload
        )
        self._incoming_packets.append(packet)

    def receive(self) -> Optional[Packet]:
        """Return the next incoming packet if available"""
        if self._incoming_packets:
            return self._incoming_packets.popleft()
        return None

    def get_peers(self) -> List[str]:
        """Return a static list of dummy peers"""
        return self._peers.copy()
    
    def get_sender_id(self) -> str:
        """Return the node's sender ID"""
        return self.node_id


# Example usage
if __name__ == "__main__":
    secure_lora = DummySecureLoRa("raspberry-pi-001")

    # Simulate sending messages
    secure_lora.send(MsgType.DATA, b"Hello World!")
    secure_lora.send(MsgType.DATA, b"Test message 2")

    # Simulate receiving messages
    packet = secure_lora.receive()
    while packet:
        print(f"Received packet from {packet.sender_id}: {packet.get_payload_as_string()}")
        packet = secure_lora.receive()

    print("Peers:", secure_lora.get_peers())
