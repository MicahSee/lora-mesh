import os
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from secure_lora.constants import MsgType

# =====================================================
# App Factory
# =====================================================

def create_app(secure_lora):
    app = FastAPI()

    # Attach SecureLoRa to app state
    app.state.secure_lora = secure_lora
    app.state.current_node_id = secure_lora.get_sender_id()
    app.state.current_node_name = secure_lora.get_sender_id()

    # ---------------------- CORS ----------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------- Static Files ----------------------
    # Serve React build from frontend/dist
    static_dir = Path(__file__).parent.parent / "frontend" / "dist"
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        print(f"[STATIC] Serving React app from {static_dir}")
    else:
        print(f"[STATIC] React build not found at {static_dir}. Run 'npm run build' in frontend/")

    register_routes(app)
    register_background_tasks(app)

    return app


# =====================================================
# Data Models
# =====================================================

class Message(BaseModel):
    id: str
    sender: str
    recipient: str
    content: str
    timestamp: str
    status: str = "sent"

class MessageCreate(BaseModel):
    recipient: str
    content: str

class Node(BaseModel):
    id: str
    name: str
    last_seen: str
    signal_strength: Optional[int] = None

class Config(BaseModel):
    node_name: str


# =====================================================
# In-memory Storage
# =====================================================

messages: List[Message] = []
nodes: Dict[str, Node] = {}
active_connections: List[WebSocket] = []

# =====================================================
# WebSocket Helper
# =====================================================

async def notify_websockets(msg: dict):
    for ws in active_connections.copy():
        try:
            await ws.send_json(msg)
        except Exception:
            active_connections.remove(ws)


# =====================================================
# Routes
# =====================================================

def register_routes(app: FastAPI):

    @app.get("/")
    async def root():
        return {"message": "Secure LoRa Mesh Network API", "node_id": app.state.current_node_id}

    @app.get("/api/nodes", response_model=List[Node])
    async def get_nodes(request: Request):
        secure_lora = request.app.state.secure_lora

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
        return messages
    
    @app.get("/api/config")
    async def get_config(request: Request):
        return {
            "node_id": request.app.state.current_node_id,
            "node_name": request.app.state.current_node_name
        }

    @app.post("/api/config")
    async def update_config(config: Config, request: Request):
        # Update the current node name
        request.app.state.current_node_name = config.node_name
        return {"message": "Configuration updated successfully."}

    @app.post("/api/messages")
    async def send_message(message: MessageCreate, request: Request):
        secure_lora = request.app.state.secure_lora

        new_message = Message(
            id=f"{app.state.current_node_id}_{len(messages)}_{datetime.now().isoformat()}",
            sender=app.state.current_node_id,
            recipient=message.recipient,
            content=message.content,
            timestamp=datetime.now().isoformat(),
            status="sent",
        )  

        try:
            secure_lora.send(MsgType.DATA, message.content.encode("utf-8"))
            messages.append(new_message)
        except Exception as e:
            new_message.status = "failed"
            messages.append(new_message)
            print(f"Failed to send message: {e}")

        return new_message

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        active_connections.append(websocket)

        try:
            while True:
                data = await websocket.receive_text()
                print(f"WebSocket received: {data}")
        except WebSocketDisconnect:
            active_connections.remove(websocket)

    # ---------------------- Serve React App (catch-all, must be last) ----------------------
    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        """Serve React app for all non-API routes"""
        static_dir = Path(__file__).parent.parent / "frontend" / "dist"

        if not static_dir.exists():
            return {
                "error": "React app not built",
                "message": "Run 'npm run build' in the frontend directory",
                "path": str(static_dir)
            }

        # Check if the requested file exists
        if full_path and full_path != "":
            file_path = static_dir / full_path
            if file_path.exists() and file_path.is_file():
                return FileResponse(file_path)

        # For all other paths (including root), serve index.html
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

        return {"error": "index.html not found", "path": str(index_path)}


# =====================================================
# Background Tasks
# =====================================================

def register_background_tasks(app: FastAPI):

    @app.on_event("startup")
    async def startup_event():
        asyncio.create_task(discover_nodes(app))
        asyncio.create_task(listen_for_lora_messages(app))


async def discover_nodes(app: FastAPI):
    secure_lora = app.state.secure_lora

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


async def listen_for_lora_messages(app: FastAPI):
    secure_lora = app.state.secure_lora

    while True:
        try:
            packet = secure_lora.receive()
            if packet:
                content_str = packet.get_payload_as_string()
                sender = str(packet.sender_id)

                incoming_msg = Message(
                    id=f"{sender}_{len(messages)}_{datetime.now().isoformat()}",
                    sender=sender,
                    recipient=app.state.current_node_id,
                    content=content_str,
                    timestamp=datetime.now().isoformat(),
                    status="received",
                )

                messages.append(incoming_msg)

                await notify_websockets({
                    "type": "new_message",
                    "data": incoming_msg.dict(),
                })

        except Exception as e:
            print(f"Error receiving secure LoRa message: {e}")

        await asyncio.sleep(1)
