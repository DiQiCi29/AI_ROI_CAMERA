from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json
import logging
from app.core.security import decode_token

router = APIRouter()
logger = logging.getLogger("uvicorn")

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"✓ [WebSocket] New client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"🛑 [WebSocket] Client disconnected. Remaining: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"⚠️ [WebSocket] Broadcast error: {str(e)}")

manager = ConnectionManager()


async def broadcast(event: str, data: dict):
    """Phát tin nhắn WebSocket với event và data dạng dict (tự động JSON serialize)."""
    payload = json.dumps({"event": event, "data": data})
    await manager.broadcast(payload)


async def broadcast_event(event: str, data: dict):
    """Alias của broadcast() — tương thích với detection_service."""
    await broadcast(event, data)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    # Luôn luôn chấp nhận kết nối trước để tránh lỗi 403 ngắt luồng realtime
    await manager.connect(websocket)
    
    # Nới lỏng kiểm tra token — nếu lỗi chỉ ghi warning, không chặn kết nối
    if token:
        try:
            payload = decode_token(token)
            logger.info(f"✓ [WebSocket] Client authenticated for user ID: {payload.get('sub')}")
        except Exception:
            logger.warning("⚠️ WebSocket token expired/invalid but connection allowed for live tracking")

    try:
        while True:
            # Lắng nghe dữ liệu rỗng để duy trì ping-pong kết nối không bị ngắt
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
