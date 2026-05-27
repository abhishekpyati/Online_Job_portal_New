from collections import defaultdict

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.models import Notification


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[user_id].append(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        if websocket in self.active_connections[user_id]:
            self.active_connections[user_id].remove(websocket)

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        dead_connections: list[WebSocket] = []
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                dead_connections.append(websocket)
        for websocket in dead_connections:
            self.disconnect(user_id, websocket)

    async def send_to_all(self, payload: dict) -> None:
        dead_connections: list[WebSocket] = []
        for sockets in self.active_connections.values():
            for websocket in sockets:
                try:
                    await websocket.send_json(payload)
                except RuntimeError:
                    dead_connections.append(websocket)
        for websocket in dead_connections:
            for user_id, sockets in list(self.active_connections.items()):
                if websocket in sockets:
                    self.disconnect(user_id, websocket)


manager = ConnectionManager()


async def create_notification(db: Session, user_id: int, message: str) -> Notification:
    notification = Notification(user_id=user_id, message=message)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    await manager.send_to_user(
        user_id,
        {"type": "notification", "id": notification.id, "message": notification.message, "created_at": notification.created_at.isoformat()},
    )
    return notification
