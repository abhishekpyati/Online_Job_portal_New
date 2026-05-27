from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import decode_access_token
from app.db.session import SessionLocal, get_db
from app.models import Notification, User
from app.schemas.notifications import NotificationRead
from app.services.notifications import manager

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Notification]:
    return db.query(Notification).filter(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()).limit(50).all()


@router.put("/{notification_id}/read", response_model=NotificationRead)
def mark_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Notification:
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.websocket("/ws")
async def notifications_ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    payload = decode_access_token(token or "")
    if not payload or not payload.get("sub"):
        await websocket.close(code=1008)
        return
    user_id = int(payload["sub"])
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first():
            await websocket.close(code=1008)
            return
        await manager.connect(user_id, websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
    finally:
        db.close()
