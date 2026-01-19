import socket
import struct
import threading
import json
import time
from datetime import datetime

MCAST_GRP = "224.0.0.251"  # Multicast group address


class P2PNode:
    def __init__(self, node_name, port=5000, discovery_port=5001):
        self.node_name = node_name
        self.port = port
        self.discovery_port = discovery_port
        self.peers = {}  # {name: {'ip': ip, 'port': port, 'last_seen': timestamp}}
        self.inbox = []  # List of received messages
        self.unread_count = 0
        self.running = False

    def start(self):
        """Start the P2P node with discovery and messaging"""
        self.running = True

        # Start discovery beacon (announces presence)
        discovery_thread = threading.Thread(target=self._send_discovery_beacon)
        discovery_thread.daemon = True
        discovery_thread.start()

        # Start discovery listener (finds peers)
        listener_thread = threading.Thread(target=self._listen_discovery)
        listener_thread.daemon = True
        listener_thread.start()

        # Start message receiver
        receiver_thread = threading.Thread(target=self._receive_messages)
        receiver_thread.daemon = True
        receiver_thread.start()

        print(f"[{self.node_name}] Node started on port {self.port}")
        print(
            f"[{self.node_name}] Using multicast group {MCAST_GRP}:{self.discovery_port}")

    def _send_discovery_beacon(self):
        """Send multicast discovery beacons every 3 seconds"""
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Set TTL (time-to-live) for multicast packets
        # TTL=2 means packets can traverse one router
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        beacon_data = json.dumps({
            'type': 'discovery',
            'name': self.node_name,
            'port': self.port
        })

        while self.running:
            try:
                # Send to multicast group instead of broadcast
                sock.sendto(beacon_data.encode(),
                            (MCAST_GRP, self.discovery_port))
                time.sleep(3)
            except Exception as e:
                print(f"[{self.node_name}] Beacon error: {e}")
                time.sleep(3)

    def _listen_discovery(self):
        """Listen for multicast discovery beacons from other peers"""
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind to the discovery port on all interfaces
        sock.bind(('', self.discovery_port))

        # Join the multicast group
        mreq = struct.pack("4sl", socket.inet_aton(
            MCAST_GRP), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        print(
            f"[{self.node_name}] Listening for peers on multicast group {MCAST_GRP}")

        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                beacon = json.loads(data.decode())

                if beacon['type'] == 'discovery' and beacon['name'] != self.node_name:
                    peer_ip = addr[0]
                    peer_name = beacon['name']
                    peer_port = beacon['port']

                    # Add or update peer
                    if peer_name not in self.peers:
                        print(
                            f"\n[{self.node_name}] Discovered peer: {peer_name} at {peer_ip}:{peer_port}")
                        print("> ", end='', flush=True)

                    self.peers[peer_name] = {
                        'ip': peer_ip,
                        'port': peer_port,
                        'last_seen': time.time()
                    }
            except Exception as e:
                if self.running:
                    print(f"[{self.node_name}] Discovery error: {e}")

    def _receive_messages(self):
        """Receive messages from peers"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.port))
        sock.listen(5)

        while self.running:
            try:
                conn, addr = sock.accept()
                threading.Thread(target=self._handle_connection,
                                 args=(conn, addr)).start()
            except Exception as e:
                pass

    def _handle_connection(self, conn, addr):
        """Handle incoming message connection"""
        try:
            data = conn.recv(4096).decode()
            message = json.loads(data)

            # Add message to inbox
            inbox_entry = {
                'from': message['from'],
                'text': message['text'],
                'timestamp': message['timestamp'],
                'received_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'read': False
            }
            self.inbox.append(inbox_entry)
            self.unread_count += 1

            # Notify user of new message
            print(
                f"\n* New message from {message['from']} ({self.unread_count} unread)")
            print("> ", end='', flush=True)

            conn.close()
        except Exception as e:
            pass

    def send_message(self, peer_name, text):
        """Send a message to a specific peer"""
        if peer_name not in self.peers:
            print(
                f"Unknown peer: {peer_name}. Use 'list' to see available peers.")
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)

            peer_ip = self.peers[peer_name]['ip']
            peer_port = self.peers[peer_name]['port']
            sock.connect((peer_ip, peer_port))

            message = json.dumps({
                'from': self.node_name,
                'text': text,
                'timestamp': time.time()
            })

            sock.send(message.encode())
            sock.close()
            print(f"Message sent to {peer_name}")
            return True
        except Exception as e:
            print(f"Failed to send message to {peer_name}: {e}")
            return False

    def broadcast_message(self, text):
        """Send message to all known peers"""
        sent = 0
        for peer_name in self.peers:
            if self.send_message(peer_name, text):
                sent += 1
        return sent

    def show_inbox(self):
        """Display inbox with all messages in table format"""
        if not self.inbox:
            print("\nInbox is empty")
            return

        print(f"\n{'='*80}")
        print(
            f"INBOX ({len(self.inbox)} messages, {self.unread_count} unread)")
        print(f"{'='*80}")
        print(f"{'#':<4} {'From':<15} {'Time':<20} {'Status':<8} {'Message':<30}")
        print(f"{'-'*80}")

        for idx, msg in enumerate(self.inbox, 1):
            status = "UNREAD" if not msg['read'] else "read"
            message_preview = msg['text'][:30] + \
                "..." if len(msg['text']) > 30 else msg['text']
            print(
                f"{idx:<4} {msg['from']:<15} {msg['received_at']:<20} {status:<8} {message_preview:<30}")

        print(f"{'='*80}\n")

        # Mark all as read
        for msg in self.inbox:
            msg['read'] = True
        self.unread_count = 0

    def read_message(self, msg_num):
        """Read a specific message by number"""
        if msg_num < 1 or msg_num > len(self.inbox):
            print(f"Invalid message number. Use 1-{len(self.inbox)}")
            return

        msg = self.inbox[msg_num - 1]
        print(f"\n{'='*80}")
        print(f"Message #{msg_num}")
        print(f"{'='*80}")
        print(f"From:     {msg['from']}")
        print(f"Time:     {msg['received_at']}")
        print(f"Message:\n{msg['text']}")
        print(f"{'='*80}\n")

        # Mark as read
        if not msg['read']:
            msg['read'] = True
            self.unread_count -= 1

    def clear_inbox(self):
        """Clear all messages from inbox"""
        self.inbox.clear()
        self.unread_count = 0
        print("Inbox cleared")

    def list_peers(self):
        """List all discovered peers"""
        if not self.peers:
            print("No peers discovered yet")
            return

        print("\nDiscovered Peers:")
        for name, info in self.peers.items():
            print(f"  {name} - {info['ip']}:{info['port']}")
        print()

    def stop(self):
        """Stop the node"""
        self.running = False

    def get_num_peers(self):
        """Return the number of discovered peers"""
        return len(self.peers)


# Example usage
if __name__ == "__main__":
    import sys

    # Get node name from command line or use default
    node_name = sys.argv[1] if len(sys.argv) > 1 else f"{socket.gethostname()}"

    # Create and start node
    node = P2PNode(node_name)
    node.start()

    time.sleep(1)  # Give some time to start

    print("\nCommands:")
    print("  list           - Show discovered peers")
    print("  send <name>    - Send message to specific peer")
    print("  broadcast      - Send message to all peers")
    print("  inbox          - View all messages")
    print("  read <num>     - Read specific message")
    print("  clear          - Clear inbox")
    print("  quit           - Exit")
    print()

    # Command loop
    try:
        while True:
            cmd = input("> ").strip()

            if cmd == "list":
                node.list_peers()

            elif cmd.startswith("send "):
                parts = cmd.split(maxsplit=1)
                if len(parts) == 2:
                    peer_name = parts[1]
                    msg = input("Message: ")
                    node.send_message(peer_name, msg)
                else:
                    print("Usage: send <peer_name>")

            elif cmd == "broadcast":
                msg = input("Message: ")
                sent = node.broadcast_message(msg)
                print(
                    f"Broadcasted to {sent} {'peer' if (node.get_num_peers() == 1) else 'peers'}")

            elif cmd == "inbox":
                node.show_inbox()

            elif cmd.startswith("read "):
                try:
                    msg_num = int(cmd.split()[1])
                    node.read_message(msg_num)
                except (ValueError, IndexError):
                    print("Usage: read <message_number>")

            elif cmd == "clear":
                node.clear_inbox()

            elif cmd == "quit":
                break

    except KeyboardInterrupt:
        pass

    node.stop()
    print("\nNode stopped")

