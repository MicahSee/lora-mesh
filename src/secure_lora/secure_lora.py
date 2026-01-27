from .constants import *
from .packet import Packet
from .keystore import KeyStore

import threading
import queue
import time
from collections import defaultdict

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class SecureLoRa:
    def __init__(self, radio, sender_id, key_store: 'KeyStore', debug: bool = False):
        self.radio = radio
        self.sender_id = sender_id
        self.key_store = key_store
        self.counter = 0
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
        if msg_type != MsgType.DISCOVERY:
            self.counter += 1

        # Get encryption key
        key = self.key_store.get_key(self.sender_id)
        if not key:
            raise ValueError(f"No key for sender {self.sender_id}")

        # Use counter + sender_id as a 12-byte nonce (8+4)
        nonce = self.counter.to_bytes(8, "big") + self.sender_id.to_bytes(4, "big")

        # Encrypt payload with AES-GCM
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, auth_tag = cipher.encrypt_and_digest(payload)

        # Build packet
        packet = Packet(
            version=PROTOCOL_VERSION,
            sender_id=self.sender_id,
            msg_type=msg_type,
            payload=ciphertext,
            auth_tag=auth_tag,   # reuse auth_tag field for AES-GCM tag
            nonce=nonce
        )

        if self.debug and msg_type != MsgType.DISCOVERY:
            print(f"Sending packet | type={msg_type} counter={self.counter}")

        self.radio.send(packet.serialize())

    def receive(self, timeout: float | None = 0.0) -> Packet | None:
        try:
            return self._rx_queue.get(block=True, timeout=timeout)
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

        # Ignore self
        if packet.sender_id == self.sender_id:
            if self.debug:
                print("Ignoring own packet")
            return None

        key = self.key_store.get_key(packet.sender_id)
        if not key:
            if self.debug:
                print("Unknown sender, dropping packet")
            return None

        # Reconstruct nonce
        cipher = AES.new(key, AES.MODE_GCM, nonce=packet.nonce)

        try:
            # Decrypt and verify tag
            plaintext = cipher.decrypt_and_verify(packet.payload, packet.auth_tag)
        except ValueError:
            if self.debug:
                print("AES-GCM authentication failed")
            return None

        # Replace payload with plaintext
        packet.payload = plaintext

        return packet

    def _handle_discovery(self, packet):
        if self.debug:
            print(f"Discovery from {hex(packet.sender_id)}")

        if not self.key_store.has_sender(packet.sender_id):
            if self.debug:
                print(f"Peer discovered but not recognized: {hex(packet.sender_id)}")
        else:
            self.peers[packet.sender_id]['last_seen'] = time.time()

    def get_peers(self):
        return self.peers

    def get_sender_id(self):
        return self.sender_id

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        return False
