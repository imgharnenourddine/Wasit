from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.schemas.chat import ChatChannelResponse, ChatMessageResponse, SendMessageRequest
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/channels", response_model=list[ChatChannelResponse])
async def list_my_channels(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ChatChannelResponse]:
    """List all chat channels the current user belongs to."""
    channels = await chat_service.get_user_channels(db, user.id)
    return [ChatChannelResponse.model_validate(c) for c in channels]


@router.get("/channels/{channel_id}/messages", response_model=list[ChatMessageResponse])
async def get_channel_history(
    channel_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[ChatMessageResponse]:
    """Fetch recent message history for a channel (must be a member)."""
    # Membership check
    channels = await chat_service.get_user_channels(db, user.id)
    if not any(c.id == channel_id for c in channels):
        raise HTTPException(status_code=403, detail="Not a member of this channel")
        
    messages = await chat_service.get_channel_messages(db, channel_id)
    return [ChatMessageResponse.from_model(m) for m in messages]


@router.post("/channels/{channel_id}/messages", response_model=ChatMessageResponse)
async def post_message(
    channel_id: UUID,
    payload: SendMessageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> ChatMessageResponse:
    """Send a message to a channel. Triggers AI Delegate if applicable."""
    # Membership check
    channels = await chat_service.get_user_channels(db, user.id)
    if not any(c.id == channel_id for c in channels):
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    msg = await chat_service.send_message(db, channel_id, user.id, payload.content)
    return ChatMessageResponse.from_model(msg)


@router.websocket("/ws/{channel_id}")
async def ws_chat(websocket: WebSocket, channel_id: str, token: str) -> None:
    """WebSocket endpoint for real-time channel communication."""
    # 1. Auth check
    try:
        payload = await decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=1008)
            return
        user_id = UUID(payload.get("sub"))
    except Exception:
        await websocket.close(code=1008)
        return

    # 2. Membership check (using a fresh session for the WS)
    from app.core.database import SessionLocal
    async with SessionLocal() as db:
        channels = await chat_service.get_user_channels(db, user_id)
        if not any(str(c.id) == channel_id for c in channels):
            await websocket.close(code=1003)
            return

    # 3. Connect to manager
    await chat_service.manager.connect(websocket, channel_id)
    try:
        while True:
            # We don't process incoming messages *via* WS here to keep persistence logic in POST
            # But the client can keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        chat_service.manager.disconnect(websocket, channel_id)
