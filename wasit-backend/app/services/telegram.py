from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.delegate_intent import infer_delegate_intent
from app.models.delegate_data import AIDelegateConfig
from app.models.institution import Class
from app.models.student import Student
from app.models.telegram import TelegramGroup, TelegramMessage
from app.models.user import Role, User
from app.services.ai_delegate_tools import autonomous_reply_from_tools
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


async def send_telegram_text(
    db: AsyncSession, group: TelegramGroup, chat_id: str, text: str
) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{group.bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text[:4096]}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            ok = bool(data.get("ok"))
            return ok, "" if ok else "telegram_api_not_ok"
    except Exception as exc:
        return False, f"telegram_error:{type(exc).__name__}:{exc}"


async def send_telegram_poll(
    db: AsyncSession, group: TelegramGroup, chat_id: str, question: str, options: list[str]
) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{group.bot_token}/sendPoll"
    payload = {
        "chat_id": chat_id,
        "question": question[:300],
        "options": [o[:100] for o in options[:10]],
        "is_anonymous": False,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            ok = bool(data.get("ok"))
            return ok, "" if ok else "telegram_api_not_ok"
    except Exception as exc:
        return False, f"telegram_error:{type(exc).__name__}"


async def send_to_group(db: AsyncSession | None, class_id: str, message: str) -> dict[str, str | bool]:
    if db is None:
        return {"class_id": class_id, "sent": False, "reason": "db_not_provided"}
    class_uuid = UUID(class_id)
    result = await db.execute(select(TelegramGroup).where(TelegramGroup.class_id == class_uuid))
    group = result.scalar_one_or_none()
    if not group:
        return {"class_id": class_id, "sent": False, "reason": "group_not_registered"}

    sent, reason = await send_telegram_text(db, group, group.chat_id, message)
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


@dataclass
class _ResolvedContext:
    class_id: UUID
    group: TelegramGroup
    reply_chat_id: str
    filiere_poll_threshold: int


async def _resolve_group_chat(db: AsyncSession, chat_id: str) -> _ResolvedContext | None:
    result = await db.execute(select(TelegramGroup).where(TelegramGroup.chat_id == chat_id))
    group = result.scalar_one_or_none()
    if not group:
        return None
    c = await db.execute(
        select(Class).where(Class.id == group.class_id).options(selectinload(Class.filiere))
    )
    class_row = c.scalar_one_or_none()
    if not class_row:
        return None
    threshold = class_row.filiere.aggregation_poll_threshold
    return _ResolvedContext(
        class_id=group.class_id,
        group=group,
        reply_chat_id=chat_id,
        filiere_poll_threshold=threshold,
    )


async def _resolve_private_chat(db: AsyncSession, from_id: int, chat_id: str) -> _ResolvedContext | None:
    uid = str(from_id)
    user = await db.scalar(select(User).where(User.telegram_user_id == uid))
    if not user:
        return None
    student = await db.scalar(select(Student).where(Student.user_id == user.id))
    if not student:
        return None
    result = await db.execute(select(TelegramGroup).where(TelegramGroup.class_id == student.class_id))
    group = result.scalar_one_or_none()
    if not group:
        return None
    c = await db.execute(
        select(Class).where(Class.id == student.class_id).options(selectinload(Class.filiere))
    )
    class_row = c.scalar_one_or_none()
    if not class_row:
        return None
    threshold = class_row.filiere.aggregation_poll_threshold
    return _ResolvedContext(
        class_id=student.class_id,
        group=group,
        reply_chat_id=chat_id,
        filiere_poll_threshold=threshold,
    )


async def _ai_delegate_active(db: AsyncSession, class_id: UUID) -> bool:
    row = await db.scalar(select(AIDelegateConfig).where(AIDelegateConfig.class_id == class_id))
    return bool(row and row.is_active)


async def _find_student_for_class(db: AsyncSession, telegram_user_id: str, class_id: UUID) -> Student | None:
    return await db.scalar(
        select(Student)
        .join(User, Student.user_id == User.id)
        .where(User.telegram_user_id == telegram_user_id, Student.class_id == class_id)
    )


async def _handle_telegram_message(db: AsyncSession, payload: dict) -> dict[str, str | bool]:
    msg = payload.get("message") or {}
    if msg.get("from", {}).get("is_bot"):
        return {"ok": True, "skipped": True, "reason": "from_bot"}

    text = (msg.get("text") or "").strip()
    if not text:
        return {"ok": True, "skipped": True, "reason": "no_text"}

    chat = msg.get("chat") or {}
    chat_id = str(chat.get("id", ""))
    chat_type = chat.get("type", "private")
    from_id = msg.get("from", {}).get("id")
    if from_id is None:
        return {"ok": False, "reason": "no_from"}

    ctx: _ResolvedContext | None = None
    if chat_type in ("group", "supergroup"):
        ctx = await _resolve_group_chat(db, chat_id)
    elif chat_type == "private":
        ctx = await _resolve_private_chat(db, int(from_id), chat_id)

    if not ctx:
        return {"ok": True, "skipped": True, "reason": "unregistered_chat_or_user"}

    cfg = await _ai_delegate_active(db, ctx.class_id)
    db.add(TelegramMessage(group_id=ctx.group.id, direction="in", message_text=text))
    await db.commit()

    if not cfg:
        return {"ok": True, "accepted": True, "reason": "ai_delegate_inactive"}

    auto = await autonomous_reply_from_tools(db, ctx.class_id, text)
    if auto:
        sent, err = await send_telegram_text(db, ctx.group, ctx.reply_chat_id, auto)
        if sent:
            db.add(TelegramMessage(group_id=ctx.group.id, direction="out", message_text=auto))
            await db.commit()
        return {"ok": True, "accepted": True, "autonomous": True, "sent": sent, "err": err}

    intent = infer_delegate_intent(text, similar_count=0, poll_threshold=ctx.filiere_poll_threshold)
    if intent == "autonomous_answer":
        fallback = (
            "Je n’ai pas trouvé cette information dans les données à jour de la classe "
            "(emploi du temps, examens, trombinoscope)."
        )
        sent, _ = await send_telegram_text(db, ctx.group, ctx.reply_chat_id, fallback)
        if sent:
            db.add(TelegramMessage(group_id=ctx.group.id, direction="out", message_text=fallback))
            await db.commit()
        return {"ok": True, "accepted": True, "autonomous": False, "missing_data": True}

    if intent == "poll_needed":
        ok, err = await send_telegram_poll(
            db,
            ctx.group,
            ctx.reply_chat_id,
            question=text[:200] or "Sondage",
            options=["Oui", "Non", "Abstention"],
        )
        return {"ok": True, "accepted": True, "poll": ok, "err": err}

    stu = await _find_student_for_class(db, str(from_id), ctx.class_id)
    if stu and intent in ("aggregate_request", "unknown"):
        await create_ticket_from_problem(
            db=db, student_id=stu.id, class_id=ctx.class_id, raw_text=text
        )
        reply = "Votre demande a été enregistrée et transmise."
        sent, _ = await send_telegram_text(db, ctx.group, ctx.reply_chat_id, reply)
        if sent:
            db.add(TelegramMessage(group_id=ctx.group.id, direction="out", message_text=reply))
            await db.commit()
        return {"ok": True, "accepted": True, "ticket": True}

    user = await db.scalar(select(User).where(User.telegram_user_id == str(from_id)))
    if user and user.role == Role.teacher:
        hint = (
            "Message reçu (enseignant). Les questions d’emploi du temps / examens peuvent être posées ici; "
            "pour le suivi de demandes élèves, utilisez le canal habituel."
        )
        sent, _ = await send_telegram_text(db, ctx.group, ctx.reply_chat_id, hint)
        if sent:
            db.add(TelegramMessage(group_id=ctx.group.id, direction="out", message_text=hint))
            await db.commit()
        return {"ok": True, "accepted": True, "teacher": True}

    link_msg = (
        "Liez votre compte Telegram à Wasit (profil étudiant) pour que le délégué IA puisse enregistrer "
        "vos demandes."
    )
    sent, _ = await send_telegram_text(db, ctx.group, ctx.reply_chat_id, link_msg)
    if sent:
        db.add(TelegramMessage(group_id=ctx.group.id, direction="out", message_text=link_msg))
        await db.commit()
    return {"ok": True, "accepted": True, "needs_link": True}


async def handle_incoming_webhook(db: AsyncSession, payload: dict) -> dict[str, str | bool]:
    if "message" in payload:
        return await _handle_telegram_message(db, payload)

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
