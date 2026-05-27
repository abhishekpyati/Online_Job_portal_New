from datetime import datetime

from app.schemas.common import ORMModel


class NotificationRead(ORMModel):
    id: int
    user_id: int
    message: str
    is_read: bool
    created_at: datetime
