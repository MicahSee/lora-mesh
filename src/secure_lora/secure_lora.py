from .constants import *
from .packet import Packet
from .crypto import compute_hmac, verify_hmac
from .replay import ReplayProtection
from .keystore import KeyStore

import threading
import queue
import time
from collections import defaultdict


class SecureLoRa:
    def __init__(self, radio, sender_id, key_store: 'KeyStore', debug: bool = False):
        self.radio = radio
        self.sender_id = sender_id
        self.key_store = key_store
        self.counter = 0
        self.replay = ReplayProtection()
        self.debug = debug
        self.peers = defaultdict(dict)

        # RX
        self._rx_queue = queue.Queue()
        self._running = True
        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            daemon=True
        )
        self._rx_thread.start()

        # Discovery TX
        self._discovery_interval = 5.0  # seconds
        self._discovery_thread = threading.Thread(
            target=self._discovery_loop,
            daemon=True
        )
        self._discovery_thread.start()

    # ------------------------
    # Public API
    # ------------------------

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

        if self.debug:
            print(f"Sending packet | type={msg_type} counter={self.counter}")

        self.radio.send(packet.serialize())

    def receive(self, timeout: float | None = None):
        """
        Client-facing receive.
        Returns:
            Packet or None
        """
        try:
            return self._rx_queue.get(block=False)
        except queue.Empty:
            return None

    def _discovery_loop(self):
        time.sleep(1.0)

        while self._running:
            self._send_discovery()
            time.sleep(self._discovery_interval)

    def _send_discovery(self):
        payload = self.sender_id.to_bytes(4, "big")
        self.send(MsgType.DISCOVERY, payload)

    def stop(self):
        self._running = False
        self._rx_thread.join(timeout=1.0)
        self._discovery_thread.join(timeout=1.0)

    # ------------------------
    # Background RX logic
    # ------------------------

    def _rx_loop(self):
        while self._running:
            data = self.radio.receive()

            if not data:
                time.sleep(0.01)
                continue

            packet = self._process_raw_packet(data)
            if not packet:
                continue

            # Protocol-level handling
            if packet.msg_type == MsgType.DISCOVERY:
                self._handle_discovery(packet)
                continue

            # Application-level packets only
            self._rx_queue.put(packet)

    def _process_raw_packet(self, data):
        try:
            packet = Packet.parse(data)
        except Exception:
            if self.debug:
                print("Failed to parse packet")
            return None

        if self.debug:
            print(f"Received packet from {hex(packet.sender_id)}")
            print(f"  Type: {packet.msg_type}")
            print(f"  Counter: {packet.counter}")

        # Ignore self
        if packet.sender_id == self.sender_id:
            return None

        key = self.key_store.get_key(packet.sender_id)
        if not key:
            if self.debug:
                print("Unknown sender, dropping packet")
            return None

        raw = packet.serialize_without_hmac()
        if not verify_hmac(key, raw, packet.hmac):
            if self.debug:
                print("HMAC verification failed")
            return None

        if not self.replay.check_and_update(packet.sender_id, packet.counter):
            if self.debug:
                print("Replay detected")
            return None

        return packet

    def _handle_discovery(self, packet):
        if self.debug:
            print(f"Discovery from {hex(packet.sender_id)}")

        # Example behavior:
        # - mark node as seen
        # - update last-seen timestamp
        # - optionally respond

        if not self.key_store.has_sender(packet.sender_id):
            if self.debug:
                print(f"Peer discovered but not recognized: {hex(packet.sender_id)}")
        else:
            self.peers[packet.sender_id]['last_seen'] = time.time()
        # Optional: reply to discovery
        # self.send(MsgType.DISCOVERY_ACK, self.sender_id.to_bytes(4, "big"))

    def get_peers(self):
        return self.peers

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        # return False → propagate exceptions (recommended)
        return False
