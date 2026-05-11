from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError
from app.core.security import decode_token
from datetime import datetime
import json

router = APIRouter(tags=["WebSocket"])

# Lưu danh sách clients đang kết nối
connected_clients: list[WebSocket] = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    # Xác thực JWT
    try:
        decode_token(token)
    except JWTError:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    connected_clients.append(websocket)

    await websocket.send_json({
        "event": "connected",
        "data": {"message": "WebSocket connected successfully",
                 "timestamp": datetime.utcnow().isoformat()}
    })

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            event = msg.get("event")

            if event == "ping":
                await websocket.send_json({
                    "event": "pong",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                })
            elif event in ("subscribe_camera", "unsubscribe_camera"):
                await websocket.send_json({
                    "event": f"{event}_ack",
                    "data": msg.get("data", {})
                })
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

# Hàm dùng để broadcast từ các service khác (AI webhook, MQTT...)
async def broadcast_event(event: str, data: dict):
    dead = []
    for client in connected_clients:
        try:
            await client.send_json({"event": event, "data": data})
        except Exception:
            dead.append(client)
    for d in dead:
        connected_clients.remove(d)