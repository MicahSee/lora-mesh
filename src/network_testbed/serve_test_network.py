import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from multiprocessing.managers import BaseManager
from contextlib import asynccontextmanager
import time
import json
import asyncio
import threading
from pathlib import Path

# --- Core Network Logic ---
def normalize_node_id(node_id):
    """Convert node_id to a string. If it's an integer, format as hex."""
    if isinstance(node_id, int):
        return f"0x{node_id:08X}"
    return str(node_id)

class LocalNetwork:
    def __init__(self, message_parser=None):
        self.messages = []  # List of dicts
        self.next_id = 0
        self.nodes = {}     # node_id -> last_seen
        self.topology = {}  # sender_id -> set(receiver_ids)
        self.traffic_log = []
        self.ws_clients = []  # List of WebSocket connections
        self.previous_nodes = set()  # Track previous node list for change detection
        self.pending_updates = []  # Queue of updates to broadcast
        self.updates_lock = threading.Lock()  # Thread-safe access to pending_updates
        self.message_parser = message_parser  # Optional callable to parse message data

    def register_node(self, node_id):
        # Normalize node_id to string (handles integers from hex like 0xA3F91C42)
        node_id = normalize_node_id(node_id)
        self.nodes[node_id] = time.time()
        if node_id not in self.topology:
            self.topology[node_id] = [] # Store as list for easy JSON serialization

        # Check if nodes have changed
        current_nodes = set(self.nodes.keys())
        if current_nodes != self.previous_nodes:
            self.previous_nodes = current_nodes.copy()
            # Queue update for broadcasting
            with self.updates_lock:
                self.pending_updates.append({
                    "type": "nodes_update",
                    "data": {
                        "nodes": list(self.nodes.keys()),
                        "topology": {k: list(v) for k, v in self.topology.items()}
                    }
                })

        return True

    def send(self, sender_id, data: bytes):
        # Normalize sender_id to string
        sender_id = normalize_node_id(sender_id)

        # Atomically get and increment message ID
        with self.updates_lock:
            msg_id = self.next_id
            self.next_id += 1

        msg_timestamp = time.time()

        # Calculate who can receive this message based on topology
        receivers = []
        if sender_id in self.topology:
            # Only include nodes that were already registered at message send time
            for receiver_id in self.topology[sender_id]:
                if receiver_id in self.nodes and self.nodes[receiver_id] <= msg_timestamp:
                    receivers.append(receiver_id)

        # Parse the message if a parser is configured
        parsed_fields = {}
        if self.message_parser:
            try:
                parsed_fields = self.message_parser(data) or {}
            except Exception as e:
                print(f"[PARSER ERROR] Failed to parse message: {e}")

        # Determine what to show in the 'data' field
        # If it's a SecureLora packet, show a cleaner message instead of encrypted garbage
        data_display = data.decode('utf-8', errors='ignore')
        if parsed_fields.get('format') == 'SecureLora':
            msg_type = parsed_fields.get('msg_type', 'UNKNOWN')
            counter = parsed_fields.get('counter', '?')
            data_display = f"[ENCRYPTED {msg_type} #{counter}]"

        msg = {
            'id': msg_id,
            'sender': sender_id,
            'data': data_display,
            'timestamp': msg_timestamp,
            'receivers': receivers,
            **parsed_fields  # Spread parsed fields into the message dict
        }

        self.messages.append({
            'id': msg_id,
            'sender': sender_id,
            'data': data,
            'timestamp': msg_timestamp
        })

        # Always add to traffic log and broadcast (no duplicate check needed, IDs are unique)
        self.traffic_log.append(msg)
        if len(self.traffic_log) > 100:
            self.traffic_log.pop(0)

        # Queue traffic update for broadcasting
        with self.updates_lock:
            self.pending_updates.append({
                "type": "traffic_update",
                "data": msg
            })

        print(f"[SEND] Message #{msg_id} from {sender_id}: {msg['data']} -> {receivers}")

        return msg_id

    def get_updates(self, receiver_id, last_id: int):
        # Normalize receiver_id to string
        receiver_id = normalize_node_id(receiver_id)

        updates = []
        receiver_join_time = self.nodes.get(receiver_id, 0)

        for m in self.messages:
            if m['id'] > last_id:
                sender = m['sender']
                msg_timestamp = m.get('timestamp', 0)

                # Only deliver messages that were sent after this node joined
                if msg_timestamp < receiver_join_time:
                    continue

                # Check if sender is allowed to talk to receiver
                if sender in self.topology and receiver_id in self.topology[sender]:
                    updates.append(m)
        return updates

    def get_full_state(self):
        return {
            "nodes": list(self.nodes.keys()),
            "topology": {k: list(v) for k, v in self.topology.items()},
            "traffic": self.traffic_log[-20:]
        }

    def toggle_link(self, sender, receiver):
        # Normalize to strings
        sender = normalize_node_id(sender)
        receiver = normalize_node_id(receiver)

        if sender not in self.topology: self.topology[sender] = []
        if receiver in self.topology[sender]:
            self.topology[sender].remove(receiver)
        else:
            self.topology[sender].append(receiver)

        # Queue topology update for broadcasting
        with self.updates_lock:
            self.pending_updates.append({
                "type": "topology_update",
                "data": {
                    "topology": {k: list(v) for k, v in self.topology.items()}
                }
            })

# --- Message Parser Example ---
# Define a custom parser function that takes raw bytes and returns a dict of parsed fields
# These fields will automatically appear as columns in the traffic log UI
def example_message_parser(data: bytes) -> dict:
    """
    Example parser that extracts fields from message data.
    Return a dict where keys become column names in the traffic log.
    """
    try:
        text = data.decode('utf-8', errors='ignore')
        # Example: parse JSON or extract metadata
        return {
            'message_length': len(data),
            'message_type': 'TEXT' if text.isprintable() else 'BINARY'
        }
    except:
        return {}

# --- SecureLora Packet Parser ---
def secure_lora_packet_parser(data: bytes) -> dict:
    """
    Parse SecureLora packet structure and extract header fields.
    Packet format: Version (1) | SenderID (4) | MsgType (1) | Nonce (12) | Payload (encrypted) | AuthTag (16)

    Note: This parser can only extract header information. The payload is encrypted and cannot
    be decrypted without the encryption keys. Decryption happens at the receiver side in SecureLora._process_raw_packet.
    """
    import struct

    # Message type mapping
    MSG_TYPES = {
        1: 'DATA',
        2: 'ACK',
        3: 'COMMAND',
        4: 'RESPONSE',
        5: 'DISCOVERY'
    }

    try:
        # Header format: "!B I B 12s" = 1 + 4 + 1 + 12 = 18 bytes
        header_size = 18
        auth_tag_size = 16

        # Check if this looks like a SecureLora packet
        if len(data) < header_size + auth_tag_size:
            # Not a SecureLora packet - probably plain text
            # Return basic info without error
            text = data.decode('utf-8', errors='ignore')
            return {
                'format': 'Plain Text',
                'size': len(data)
            }

        # Try to parse as SecureLora packet
        version, sender_id, msg_type, nonce = struct.unpack("!B I B 12s", data[:header_size])

        # Validate version (should be 1)
        if version != 1:
            # Probably not a SecureLora packet
            text = data.decode('utf-8', errors='ignore')
            return {
                'format': 'Plain Text',
                'size': len(data)
            }

        # Extract counter from nonce (first 8 bytes of nonce)
        counter = int.from_bytes(nonce[:8], "big")

        # Calculate payload size (total - header - auth_tag)
        payload_size = len(data) - header_size - auth_tag_size

        # Extract encrypted payload
        encrypted_payload = data[header_size:-auth_tag_size]

        # Try to show a preview of encrypted data as hex
        payload_preview = encrypted_payload[:16].hex() if len(encrypted_payload) > 0 else ""

        return {
            'format': 'SecureLora',
            'version': version,
            'packet_sender_id': f'0x{sender_id:08X}',
            'msg_type': MSG_TYPES.get(msg_type, f'UNKNOWN({msg_type})'),
            'counter': counter,
            'payload_size': payload_size,
            'payload_preview': f'{payload_preview}...' if len(payload_preview) == 32 else payload_preview
        }
    except Exception as e:
        # Parsing failed, treat as plain text
        return {
            'format': 'Unknown',
            'parse_error': str(e)
        }

# --- Multiprocessing Setup ---
class NetworkManager(BaseManager): pass

# Create network with SecureLora packet parser
# This will parse encrypted packet headers and display fields in the traffic log
shared_network = LocalNetwork(message_parser=secure_lora_packet_parser)
NetworkManager.register('get_network', callable=lambda: shared_network)
manager = NetworkManager(address=('127.0.0.1', 5000), authkey=b'radio_secret')
# Start the manager in its own process-managed way
mgr_server = manager.get_server()

# --- Background task for WebSocket broadcasts ---
async def broadcast_updates():
    """Background task to broadcast pending updates to all WebSocket clients"""
    while True:
        await asyncio.sleep(0.1)  # Check for updates every 100ms

        if not shared_network.ws_clients:
            continue

        # Atomically get and clear pending updates
        with shared_network.updates_lock:
            if not shared_network.pending_updates:
                continue
            updates = shared_network.pending_updates.copy()
            shared_network.pending_updates.clear()

        # Remove disconnected clients
        dead_clients = []

        for update in updates:
            message = json.dumps(update)
            if update['type'] == 'traffic_update':
                print(f"[BROADCAST] Sending traffic_update: #{update['data']['id']} {update['data']['sender']} -> {update['data']['receivers']} to {len(shared_network.ws_clients)} clients")
            for client in shared_network.ws_clients:
                try:
                    await client.send_text(message)
                except:
                    if client not in dead_clients:
                        dead_clients.append(client)

        for client in dead_clients:
            if client in shared_network.ws_clients:
                shared_network.ws_clients.remove(client)

@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager to start background tasks"""
    # Startup
    task = asyncio.create_task(broadcast_updates())
    yield
    # Shutdown
    task.cancel()

# --- FastAPI Setup ---
app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files from React build
static_dir = Path(__file__).parent / "network-ui" / "dist"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")
    print(f"[STATIC] Serving React app from {static_dir}")
else:
    print(f"[STATIC] React build not found at {static_dir}. Run 'npm run build' in network-ui/")

class LinkToggle(BaseModel):
    sender: str
    receiver: str

@app.get("/state")
def get_state():
    return shared_network.get_full_state()

@app.post("/toggle-link")
async def toggle_link(data: LinkToggle):
    shared_network.toggle_link(data.sender, data.receiver)
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    shared_network.ws_clients.append(websocket)
    print(f"[WEBSOCKET] Client connected. Total clients: {len(shared_network.ws_clients)}")

    # Send initial state
    initial_state = json.dumps({
        "type": "initial_state",
        "data": shared_network.get_full_state()
    })
    await websocket.send_text(initial_state)

    try:
        while True:
            # Keep connection alive and listen for any client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in shared_network.ws_clients:
            shared_network.ws_clients.remove(websocket)
            print(f"[WEBSOCKET] Client disconnected. Total clients: {len(shared_network.ws_clients)}")

# Serve React app (must be last - catch-all route)
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve React app for all non-API routes"""
    static_dir = Path(__file__).parent / "network-ui" / "dist"

    # If the build doesn't exist, return a helpful message
    if not static_dir.exists():
        return {
            "error": "React app not built",
            "message": "Run 'npm run build' in the network-ui directory",
            "path": str(static_dir)
        }

    # Check if the requested file exists
    if full_path and full_path != "":
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

    # For all other paths (including root), serve index.html
    # React Router will handle the routing
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)

    return {"error": "index.html not found", "path": str(index_path)}

if __name__ == "__main__":
    import threading
    # Run the Multiprocessing Manager in a background thread
    threading.Thread(target=mgr_server.serve_forever, daemon=True).start()
    print("Network Manager running on port 5000")
    # Run FastAPI
    uvicorn.run(app, host="0.0.0.0", port=8000)