from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    body: str
    type: str
    is_read: bool
    created_at: datetime


class NotificationReadResponse(BaseModel):
    id: UUID
    is_read: bool
