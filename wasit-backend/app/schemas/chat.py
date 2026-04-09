from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict

from app.models.chat import ChannelType


class ChatChannelResponse(BaseModel):
    id: uuid.UUID
    name: str | None
    type: ChannelType
    entity_id: uuid.UUID | None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    channel_id: uuid.UUID
    sender_id: uuid.UUID | None
    sender_name: str | None = None
    content: str
    is_ai: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, msg):
        sender_name = None
        if msg.sender:
            sender_name = f"{msg.sender.first_name} {msg.sender.last_name}"
        elif msg.is_ai:
            sender_name = "AI Bot"
        else:
            sender_name = "System"
            
        return cls(
            id=msg.id,
            channel_id=msg.channel_id,
            sender_id=msg.sender_id,
            sender_name=sender_name,
            content=msg.content,
            is_ai=msg.is_ai,
            created_at=msg.created_at,
        )


class SendMessageRequest(BaseModel):
    content: str
