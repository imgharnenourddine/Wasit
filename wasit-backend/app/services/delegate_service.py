from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delegate_data import AIDelegateConfig, ExamEvent, TimetableSlot
from app.models.institution import Class, Filiere
from app.models.user import Role, User
from sqlalchemy.orm import selectinload

from app.schemas.delegate import AIDelegateUpsert, ExamEventIn, TimetableSlotIn
from app.schemas.institution import ClassCreate
from app.services.institutional_service import create_class


def _parse_hhmm(s: str) -> time:
    try:
        return datetime.strptime(s.strip(), "%H:%M").time()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time (use HH:MM): {s}",
        ) from exc


async def get_class_or_404(db: AsyncSession, class_id: UUID) -> Class:
    c = await db.get(Class, class_id)
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return c


async def assert_can_manage_class(db: AsyncSession, user: User, class_id: UUID) -> Class:
    """Admin, Chef de filière (responsible), or class delegate may manage class-scoped AI data."""
    result = await db.execute(
        select(Class).where(Class.id == class_id).options(selectinload(Class.filiere))
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    if user.role.value == "admin":
        return c
    if c.filiere.responsible_id == user.id:
        return c
    if user.role == Role.delegate and c.delegate_id == user.id:
        return c
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


async def assert_can_manage_filiere(db: AsyncSession, user: User, filiere_id: UUID) -> Filiere:
    f = await db.get(Filiere, filiere_id)
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filiere not found")
    if user.role.value == "admin":
        return f
    if f.responsible_id == user.id:
        return f
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")


async def upsert_ai_delegate(db: AsyncSession, user: User, class_id: UUID, payload: AIDelegateUpsert) -> AIDelegateConfig:
    await assert_can_manage_class(db, user, class_id)
    result = await db.execute(select(AIDelegateConfig).where(AIDelegateConfig.class_id == class_id))
    row = result.scalar_one_or_none()
    if row:
        row.personality_prompt = payload.personality_prompt
        row.is_active = payload.is_active
    else:
        row = AIDelegateConfig(
            class_id=class_id,
            personality_prompt=payload.personality_prompt,
            is_active=payload.is_active,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def replace_timetable(db: AsyncSession, user: User, class_id: UUID, slots: list[TimetableSlotIn]) -> int:
    await assert_can_manage_class(db, user, class_id)
    await db.execute(delete(TimetableSlot).where(TimetableSlot.class_id == class_id))
    for s in slots:
        db.add(
            TimetableSlot(
                class_id=class_id,
                day_of_week=s.day_of_week,
                start_time=_parse_hhmm(s.start_time),
                end_time=_parse_hhmm(s.end_time),
                subject=s.subject,
                room=s.room,
                teacher_name=s.teacher_name,
            )
        )
    await db.commit()
    return len(slots)


async def add_exam_events(db: AsyncSession, user: User, class_id: UUID, events: list[ExamEventIn]) -> list[ExamEvent]:
    await assert_can_manage_class(db, user, class_id)
    out: list[ExamEvent] = []
    for e in events:
        row = ExamEvent(
            class_id=class_id,
            title=e.title,
            subject=e.subject,
            starts_at=e.starts_at,
            room=e.room,
        )
        db.add(row)
        out.append(row)
    await db.commit()
    for row in out:
        await db.refresh(row)
    return out


async def create_class_as_chef(db: AsyncSession, user: User, filiere_id: UUID, payload: ClassCreate) -> Class:
    await assert_can_manage_filiere(db, user, filiere_id)
    if payload.filiere_id != filiere_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body filiere_id must match path",
        )
    return await create_class(db, payload)


async def patch_filiere_ai_settings(db: AsyncSession, user: User, filiere_id: UUID, threshold: int) -> Filiere:
    await assert_can_manage_filiere(db, user, filiere_id)
    f = await db.get(Filiere, filiere_id)
    if not f:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filiere not found")
    f.aggregation_poll_threshold = threshold
    await db.commit()
    await db.refresh(f)
    return f
