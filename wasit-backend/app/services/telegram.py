from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telegram import TelegramGroup, TelegramMessage
from app.services.tickets import create_ticket_from_problem


async def register_group(db: AsyncSession, class_id: UUID, chat_id: str, bot_token: str) -> TelegramGroup:
    result = await db.execute(select(TelegramGroup).where(TelegramGroup.class_id == class_id))
    existing = result.scalar_one_or_none()
    if existing:
        existing.chat_id = chat_id
        existing.bot_token = bot_token
        existing.is_active = True
        await db.commit()
        await db.refresh(existing)
        return existing

    group = TelegramGroup(class_id=class_id, chat_id=chat_id, bot_token=bot_token, is_active=True)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


async def send_to_group(db: AsyncSession | None, class_id: str, message: str) -> dict[str, str | bool]:
    if db is None:
        return {"class_id": class_id, "sent": False, "reason": "db_not_provided"}
    class_uuid = UUID(class_id)
    result = await db.execute(select(TelegramGroup).where(TelegramGroup.class_id == class_uuid))
    group = result.scalar_one_or_none()
    if not group:
        return {"class_id": class_id, "sent": False, "reason": "group_not_registered"}

    sent = False
    reason = ""
    telegram_url = f"https://api.telegram.org/bot{group.bot_token}/sendMessage"
    payload = {"chat_id": group.chat_id, "text": message}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(telegram_url, json=payload)
            response.raise_for_status()
            data = response.json()
            sent = bool(data.get("ok"))
            if not sent:
                reason = "telegram_api_not_ok"
    except Exception as exc:
        sent = False
        reason = f"telegram_error:{type(exc).__name__}"

    db.add(TelegramMessage(group_id=group.id, direction="out", message_text=message))
    await db.commit()
    if sent:
        return {"class_id": class_id, "sent": True}
    return {"class_id": class_id, "sent": False, "reason": reason or "send_failed"}


async def get_messages(db: AsyncSession, class_id: UUID) -> list[TelegramMessage]:
    result = await db.execute(select(TelegramGroup).where(TelegramGroup.class_id == class_id))
    group = result.scalar_one_or_none()
    if not group:
        return []
    msg_result = await db.execute(
        select(TelegramMessage)
        .where(TelegramMessage.group_id == group.id)
        .order_by(TelegramMessage.sent_at.desc())
    )
    return list(msg_result.scalars().all())


async def handle_incoming_webhook(db: AsyncSession, payload: dict) -> dict[str, str | bool]:
    # Minimal webhook contract for now:
    # {
    #   "class_id": "<uuid>",
    #   "student_id": "<uuid>",
    #   "text": "..."
    # }
    try:
        class_id = UUID(str(payload.get("class_id")))
        student_id = UUID(str(payload.get("student_id")))
        text = str(payload.get("text", "")).strip()
    except Exception:
        return {"accepted": False, "reason": "invalid_payload"}

    if not text:
        return {"accepted": False, "reason": "empty_message"}

    await create_ticket_from_problem(db=db, student_id=student_id, class_id=class_id, raw_text=text)
    return {"accepted": True}
