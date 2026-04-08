from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.schemas.telegram import (
    TelegramMessageResponse,
    TelegramRegisterRequest,
    TelegramSendRequest,
)
from app.services.telegram import get_messages, handle_incoming_webhook, register_group, send_to_group

router = APIRouter(prefix="", tags=["telegram"])


@router.post("/telegram/webhook/{bot_token}")
async def telegram_webhook(
    bot_token: str,
    payload: dict,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict[str, str | bool]:
    _ = bot_token
    return await handle_incoming_webhook(db, payload)


@router.post("/classes/{class_id}/telegram/register")
async def register_class_group(
    class_id: UUID,
    payload: TelegramRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    _: Annotated[User, Depends(require_role("admin"))] = None,
) -> dict[str, str]:
    group = await register_group(db, class_id, payload.chat_id, payload.bot_token)
    return {"group_id": str(group.id), "class_id": str(group.class_id)}


@router.post("/classes/{class_id}/telegram/send")
async def send_class_message(
    class_id: UUID,
    payload: TelegramSendRequest,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    _: Annotated[User, Depends(require_role("delegate", "admin"))] = None,
) -> dict[str, str | bool]:
    return await send_to_group(db, str(class_id), payload.text)


@router.get("/classes/{class_id}/telegram/messages", response_model=list[TelegramMessageResponse])
async def list_class_messages(
    class_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    _: Annotated[User, Depends(require_role("delegate", "admin", "teacher"))] = None,
) -> list[TelegramMessageResponse]:
    messages = await get_messages(db, class_id)
    return [TelegramMessageResponse.model_validate(m) for m in messages]
