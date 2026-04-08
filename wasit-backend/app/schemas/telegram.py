from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TelegramRegisterRequest(BaseModel):
    chat_id: str
    bot_token: str


class TelegramSendRequest(BaseModel):
    text: str


class TelegramMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_id: UUID
    direction: str
    message_text: str
    sent_at: datetime
