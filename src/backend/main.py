import os

from dotenv import load_dotenv
import board
import busio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import asyncio
from secure_lora.constants import MsgType
from secure_lora.keystore import KeyStore
from secure_lora.platforms import RFM95xRadio
from secure_lora.secure_lora import SecureLoRa

app = FastAPI()
# -----------------------------
# Key store setup
# -----------------------------
keys = KeyStore()
keys.add_key(0xA3F91C42, b"supersecretkey123")
keys.add_key(0xB4E82D53, b"anothersecretkey")

# -----------------------------
# SPI and radio setup
# -----------------------------
spi = busio.SPI(clock=board.SCK, MOSI=board.MOSI, MISO=board.MISO)
CS = board.CE1
RESET = board.D25

radio = RFM95xRadio(spi, CS, RESET, freq_mhz=915.0, tx_power=5)

# -----------------------------
# SecureLoRa instance
# -----------------------------
load_dotenv()
secure_lora = SecureLoRa(radio, int(os.environ.get("SENDER_ID"), 16), keys, debug=True)

# ---------------------- CORS ----------------------
# Allow all origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow all domains
    allow_credentials=True,
    allow_methods=["*"],       # Allow all HTTP methods
    allow_headers=["*"],       # Allow all headers
)

# ---------------------- Data models ----------------------
class Message(BaseModel):
    id: str
    sender: str
    recipient: str
    content: str
    timestamp: str
    status: str = "sent"  # sent, received, failed

class MessageCreate(BaseModel):
    recipient: str
    content: str

class Node(BaseModel):
    id: str
    name: str
    last_seen: str
    signal_strength: Optional[int] = None

# ---------------------- In-memory storage ----------------------
messages: List[Message] = []
nodes: Dict[str, Node] = {}
active_connections: List[WebSocket] = []

CURRENT_NODE_ID = "raspberry-pi-001"

# ---------------------- WebSocket Helper ----------------------
async def notify_websockets(msg: dict):
    """Send a JSON message to all connected WebSocket clients."""
    for ws in active_connections.copy():
        try:
            await ws.send_json(msg)
        except:
            active_connections.remove(ws)

# ---------------------- HTTP Endpoints ----------------------
@app.get("/")
async def root():
    return {"message": "Secure LoRa Mesh Network API", "node_id": CURRENT_NODE_ID}

@app.get("/api/nodes", response_model=List[Node])
async def get_nodes():
    """Get list of discovered nodes from secure LoRa."""
    try:
        peers = secure_lora.get_peers()
        for peer_id in peers:
            nodes[str(peer_id)] = Node(
                id=str(peer_id),
                name=str(peer_id),
                last_seen=datetime.now().isoformat(),
            )
    except Exception as e:
        print(f"Error fetching peers: {e}")
    return list(nodes.values())

@app.get("/api/messages")
async def get_messages():
    """Get all messages."""
    return messages

@app.post("/api/messages")
async def send_message(message: MessageCreate):
    """Send a message via secure LoRa."""
    new_message = Message(
        id=f"{CURRENT_NODE_ID}_{len(messages)}_{datetime.now().isoformat()}",
        sender=CURRENT_NODE_ID,
        recipient=message.recipient,
        content=message.content,
        timestamp=datetime.now().isoformat(),
        status="sent"
    )

    try:
        # Send via secure_lora using MsgType.DATA
        secure_lora.send(MsgType.DATA, message.content.encode("utf-8"))
        messages.append(new_message)

    except Exception as e:
        new_message.status = "failed"
        messages.append(new_message)
        print(f"Failed to send message: {e}")

    return new_message

# ---------------------- WebSocket Endpoint ----------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates to clients."""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received via WebSocket: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# ---------------------- Background Tasks ----------------------
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listen_for_lora_messages())
    asyncio.create_task(discover_nodes())

async def discover_nodes():
    """Periodically refresh peers from secure LoRa."""
    while True:
        try:
            peers = secure_lora.get_peers()
            for peer_id in peers:
                nodes[str(peer_id)] = Node(
                    id=str(peer_id),
                    name=str(peer_id),
                    last_seen=datetime.now().isoformat(),
                )
        except Exception as e:
            print(f"Error discovering nodes: {e}")
        await asyncio.sleep(30)

async def listen_for_lora_messages():
    """Continuously poll secure LoRa for incoming packets."""
    while True:
        try:
            packet = secure_lora.receive()
            if packet:
                content_str = packet.get_payload_as_string()
                sender = str(packet.sender_id)
                incoming_msg = Message(
                    id=f"{sender}_{len(messages)}_{datetime.now().isoformat()}",
                    sender=sender,
                    recipient=CURRENT_NODE_ID,
                    content=content_str,
                    timestamp=datetime.now().isoformat(),
                    status="received"
                )
                messages.append(incoming_msg)

                # Notify WebSocket clients
                await notify_websockets({"type": "new_message", "data": incoming_msg.dict()})

        except Exception as e:
            print(f"Error receiving secure LoRa message: {e}")
        await asyncio.sleep(1)  # Poll every second

# ---------------------- Main ----------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
