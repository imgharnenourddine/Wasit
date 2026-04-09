"""Service for managing internal chat channels, message persistence, and real-time delivery."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List, Set, Any
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChannelMember, ChannelType, ChatChannel, ChatMessage
from app.models.user import User
from app.services.ai_delegate_tools import autonomous_reply_from_tools


class ChatManager:
    """Manages active WebSocket connections for chat channels."""

    def __init__(self):
        # channel_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel_id: str):
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = set()
        self.active_connections[channel_id].add(websocket)

    def disconnect(self, websocket: WebSocket, channel_id: str):
        if channel_id in self.active_connections:
            self.active_connections[channel_id].remove(websocket)
            if not self.active_connections[channel_id]:
                del self.active_connections[channel_id]

    async def broadcast(self, channel_id: str, message: dict):
        if channel_id in self.active_connections:
            # Create a list because set size might change during iteration
            for connection in list(self.active_connections[channel_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    # Broken connection, manager should ideally handle this via heartbeat/disconnect
                    pass


manager = ChatManager()


async def get_user_channels(db: AsyncSession, user_id: UUID) -> List[ChatChannel]:
    """List all channels a user belongs to."""
    stmt = (
        select(ChatChannel)
        .join(ChannelMember)
        .where(ChannelMember.user_id == user_id)
        .order_by(ChatChannel.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_channel_messages(
    db: AsyncSession, channel_id: UUID, limit: int = 50
) -> List[ChatMessage]:
    """Fetch message history for a channel."""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.channel_id == channel_id)
        .options(selectinload(ChatMessage.sender))
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    # Return in chronological order
    messages = list(result.scalars().all())
    return messages[::-1]


async def send_message(
    db: AsyncSession,
    channel_id: UUID,
    sender_id: UUID | None,
    content: str,
    is_ai: bool = False,
) -> ChatMessage:
    """Persist a message and broadcast it to the channel."""
    msg = ChatMessage(
        channel_id=channel_id,
        sender_id=sender_id,
        content=content,
        is_ai=is_ai,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg, ["sender"])

    # Prepare broadcast payload
    payload = {
        "id": str(msg.id),
        "channel_id": str(msg.channel_id),
        "sender_id": str(msg.sender_id) if msg.sender_id else None,
        "sender_name": f"{msg.sender.first_name} {msg.sender.last_name}" if msg.sender else ("AI Bot" if is_ai else "System"),
        "content": msg.content,
        "is_ai": msg.is_ai,
        "created_at": msg.created_at.isoformat(),
    }
    
    await manager.broadcast(str(channel_id), payload)

    # 1. Trigger AI Delegate if it's not already an AI message
    if not is_ai:
        # We need the class_id to trigger tools. 
        # For now, we assume entity_id is class_id if type is CLASS.
        channel = await db.get(ChatChannel, channel_id)
        if channel and channel.type == ChannelType.CLASS and channel.entity_id:
            ai_answer = await autonomous_reply_from_tools(db, channel.entity_id, content)
            if ai_answer:
                # Send AI response as a new message back to the same channel
                await send_message(db, channel_id, None, ai_answer, is_ai=True)

    return msg


async def sync_channel_members(
    db: AsyncSession, channel_id: UUID, entity_type: ChannelType, entity_id: UUID
) -> int:
    """Sync channel members based on the underlying entity (Class or ProjectGroup)."""
    channel = await db.get(ChatChannel, channel_id)
    if not channel:
        return 0

    added = 0
    existing_uids = await db.execute(
        select(ChannelMember.user_id).where(ChannelMember.channel_id == channel_id)
    )
    existing_uids_set = set(existing_uids.scalars().all())

    target_uids: Set[UUID] = set()

    if entity_type == ChannelType.CLASS:
        from app.models.institution import Class
        stmt = select(Class).where(Class.id == entity_id).options(selectinload(Class.students))
        cls = await db.scalar(stmt)
        if cls:
            if cls.delegate_id:
                target_uids.add(cls.delegate_id)
            target_uids.update({s.user_id for s in cls.students})
    elif entity_type == ChannelType.PROJECT:
        from app.models.student import ProjectGroup
        pg = await db.get(ProjectGroup, entity_id, options=[selectinload(ProjectGroup.members)])
        if pg:
            from app.models.student import Student
            for m in pg.members:
                # Need user_id from student
                s = await db.get(Student, m.student_id)
                if s:
                    target_uids.add(s.user_id)

    for uid in target_uids:
        if uid not in existing_uids_set:
            db.add(ChannelMember(channel_id=channel_id, user_id=uid))
            added += 1

    if added > 0:
        await db.commit()
    return added


async def get_or_create_class_channel(db: AsyncSession, class_id: UUID) -> ChatChannel:
    """Ensure a chat channel exists for a class and students/delegate are members."""
    stmt = select(ChatChannel).where(
        ChatChannel.type == ChannelType.CLASS, ChatChannel.entity_id == class_id
    )
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()

    if not channel:
        from app.models.institution import Class
        cls = await db.get(Class, class_id)
        if not cls:
            raise ValueError("Class not found")
            
        channel = ChatChannel(
            name=f"Channel {cls.name}",
            type=ChannelType.CLASS,
            entity_id=class_id,
        )
        db.add(channel)
        await db.commit()
        await db.refresh(channel)
    
    await sync_channel_members(db, channel.id, ChannelType.CLASS, class_id)
    return channel


async def get_or_create_project_channel(db: AsyncSession, group_id: UUID) -> ChatChannel:
    """Ensure a chat channel exists for a project group."""
    stmt = select(ChatChannel).where(
        ChatChannel.type == ChannelType.PROJECT, ChatChannel.entity_id == group_id
    )
    res = await db.execute(stmt)
    channel = res.scalar_one_or_none()

    if not channel:
        from app.models.student import ProjectGroup
        pg = await db.get(ProjectGroup, group_id)
        if not pg:
            raise ValueError("Project group not found")
            
        channel = ChatChannel(
            name=f"Project Group: {pg.name}",
            type=ChannelType.PROJECT,
            entity_id=group_id,
        )
        db.add(channel)
        await db.commit()
        await db.refresh(channel)
    
    await sync_channel_members(db, channel.id, ChannelType.PROJECT, group_id)
    return channel
