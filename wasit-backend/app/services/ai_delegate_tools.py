"""DB-backed tool implementations for the AI Delegate ."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delegate_data import ExamEvent, TimetableSlot
from app.models.student import Student
from app.models.user import User

_WEEKDAY_MON0 = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _day_name(dow: int) -> str:
    return _WEEKDAY_MON0[dow % 7]


async def get_timetable(
    db: AsyncSession, class_id: UUID, day_of_week: int | None = None
) -> list[dict[str, str | int | None]]:
    stmt = select(TimetableSlot).where(TimetableSlot.class_id == class_id).order_by(
        TimetableSlot.day_of_week, TimetableSlot.start_time
    )
    if day_of_week is not None:
        stmt = stmt.where(TimetableSlot.day_of_week == day_of_week)
    rows = (await db.execute(stmt)).scalars().all()
    out: list[dict[str, str | int | None]] = []
    for slot in rows:
        out.append(
            {
                "day_of_week": slot.day_of_week,
                "day": _day_name(slot.day_of_week),
                "start": slot.start_time.strftime("%H:%M"),
                "end": slot.end_time.strftime("%H:%M"),
                "subject": slot.subject,
                "room": slot.room,
                "teacher_name": slot.teacher_name,
            }
        )
    return out


async def get_exam_schedule(
    db: AsyncSession, class_id: UUID, limit: int = 10, after: datetime | None = None
) -> list[dict[str, str | None]]:
    if after is None:
        ref = datetime.now(timezone.utc)
    else:
        ref = after if after.tzinfo else after.replace(tzinfo=timezone.utc)
    stmt = (
        select(ExamEvent)
        .where(ExamEvent.class_id == class_id, ExamEvent.starts_at >= ref)
        .order_by(ExamEvent.starts_at.asc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "title": r.title,
            "subject": r.subject,
            "starts_at": r.starts_at.isoformat(),
            "room": r.room,
        }
        for r in rows
    ]


async def get_trombinoscope(
    db: AsyncSession, class_id: UUID, name_query: str | None = None, limit: int = 50
) -> list[dict[str, str | None]]:
    stmt = (
        select(Student, User)
        .join(User, Student.user_id == User.id)
        .where(Student.class_id == class_id, Student.is_active.is_(True))
    )
    if name_query:
        q = f"%{name_query.strip()}%"
        stmt = stmt.where(
            (User.first_name.ilike(q))
            | (User.last_name.ilike(q))
            | (func.concat(User.first_name, " ", User.last_name).ilike(q))
        )
    stmt = stmt.limit(limit)
    rows = (await db.execute(stmt)).all()
    return [
        {
            "first_name": u.first_name,
            "last_name": u.last_name,
            "student_number": s.student_number,
            "photo_url": s.photo_url,
        }
        for s, u in rows
    ]


async def get_class_student_count(db: AsyncSession, class_id: UUID) -> int:
    n = await db.scalar(select(func.count(Student.id)).where(Student.class_id == class_id))
    return int(n or 0)


async def get_free_slots(db: AsyncSession, class_id: UUID, week_start: date | None = None) -> list[dict[str, str]]:
    """Naive free blocks: assumes school day 08:00–18:00 Mon–Fri; gaps between timetable slots."""
    _ = week_start  # reserved for future week-scoped logic
    slots = (
        await db.execute(
            select(TimetableSlot)
            .where(TimetableSlot.class_id == class_id)
            .order_by(TimetableSlot.day_of_week, TimetableSlot.start_time)
        )
    ).scalars().all()
    by_day: dict[int, list[TimetableSlot]] = {}
    for s in slots:
        by_day.setdefault(s.day_of_week, []).append(s)

    school_start = time(8, 0)
    school_end = time(18, 0)
    free: list[dict[str, str]] = []
    for dow in range(0, 5):
        day_slots = by_day.get(dow, [])
        cursor = school_start
        for sl in day_slots:
            if sl.start_time > cursor:
                free.append(
                    {
                        "day": _day_name(dow),
                        "start": cursor.strftime("%H:%M"),
                        "end": sl.start_time.strftime("%H:%M"),
                    }
                )
            cursor = max(cursor, sl.end_time)
        if cursor < school_end:
            free.append(
                {
                    "day": _day_name(dow),
                    "start": cursor.strftime("%H:%M"),
                    "end": school_end.strftime("%H:%M"),
                }
            )
    return free


async def autonomous_reply_from_tools(db: AsyncSession, class_id: UUID, user_text: str) -> str | None:
    """Return a short natural-language answer when the message clearly maps to helper data."""
    t = user_text.lower()
    if any(k in t for k in ("exam", "examen", "contrôle", "ds", "partiel")):
        exams = await get_exam_schedule(db, class_id, limit=5)
        if not exams:
            return "Aucun examen à venir n’est enregistré pour cette classe pour l’instant."
        lines = [f"• {e['title']} — {e['starts_at']}" + (f" ({e['room']})" if e.get("room") else "") for e in exams]
        return "Prochains examens:\n" + "\n".join(lines)

    if any(k in t for k in ("emploi", "timetable", "schedule", "cours", "jeudi", "lundi", "mardi", "mercredi", "vendredi")):
        # crude day detection
        day_map = {
            "lundi": 0,
            "monday": 0,
            "mardi": 1,
            "tuesday": 1,
            "mercredi": 2,
            "wednesday": 2,
            "jeudi": 3,
            "thursday": 3,
            "vendredi": 4,
            "friday": 4,
        }
        dow: int | None = None
        for key, val in day_map.items():
            if key in t:
                dow = val
                break
        tt = await get_timetable(db, class_id, day_of_week=dow)
        if not tt:
            return (
                "Aucun créneau d’emploi du temps n’est enregistré pour cette période."
                if dow is not None
                else "L’emploi du temps de la classe n’est pas encore renseigné."
            )
        label = _day_name(dow) if dow is not None else "la semaine"
        lines = [f"• {x['start']}–{x['end']} {x['subject']}" + (f" — {x['room']}" if x.get("room") else "") for x in tt]
        return f"Cours ({label}):\n" + "\n".join(lines)

    if any(k in t for k in ("trombi", "étudiant", "student", "élève", "who is", "qui est")):
        # optional name after "étudiant" — take last word as guess
        parts = user_text.split()
        name_q = parts[-1] if len(parts) > 1 and len(parts[-1]) > 2 else None
        rows = await get_trombinoscope(db, class_id, name_query=name_q)
        if not rows:
            return "Aucun étudiant ne correspond dans le trombinoscope."
        lines = [f"• {r['first_name']} {r['last_name']}" for r in rows[:15]]
        return "Trombinoscope:\n" + "\n".join(lines)

    if any(k in t for k in ("combien", "how many", "nombre", "effectif", "students in")):
        n = await get_class_student_count(db, class_id)
        return f"Effectif enregistré pour cette classe: {n} étudiant(s)."

    return None
