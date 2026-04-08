from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.schemas.notifications import NotificationReadResponse, NotificationResponse
from app.services.notifications import get_user_notifications, manager, mark_notification_read

router = APIRouter(prefix="", tags=["notifications"])


@router.get("/notifications/me", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    user: Annotated[User, Depends(get_current_user)] = None,
) -> list[NotificationResponse]:
    notifications = await get_user_notifications(db, user.id, unread_only=unread_only)
    return [NotificationResponse.model_validate(n) for n in notifications]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationReadResponse)
async def read_notification(
    notification_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    user: Annotated[User, Depends(get_current_user)] = None,
) -> NotificationReadResponse:
    try:
        updated = await mark_notification_read(db, notification_id, user.id)
        return NotificationReadResponse(id=updated.id, is_read=updated.is_read)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.websocket("/ws/{user_id}")
async def ws_notifications(websocket: WebSocket, user_id: str, token: str) -> None:
    payload = await decode_token(token)
    if payload.get("type") != "access" or payload.get("sub") != user_id:
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
