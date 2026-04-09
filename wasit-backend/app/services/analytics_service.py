import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Class, Filiere, School
from app.models.problem import AggregationGroup
from app.models.student import Student
from app.models.ticket import Ticket, TicketCategory, TicketStatus


def _tickets_in_school(school_id: uuid.UUID):
    return (
        select(Ticket)
        .join(Class, Ticket.class_id == Class.id)
        .join(Filiere, Class.filiere_id == Filiere.id)
        .where(Filiere.school_id == school_id)
    )


async def get_school_overview(db: AsyncSession, school_id: uuid.UUID) -> dict:
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    base = _tickets_in_school(school_id)
    total = await db.scalar(select(func.count()).select_from(base.subquery()))

    open_sub = base.where(
        Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
    ).subquery()
    open_count = await db.scalar(select(func.count()).select_from(open_sub))

    resolved_sub = base.where(Ticket.status.in_([TicketStatus.resolved, TicketStatus.closed])).subquery()
    resolved_count = await db.scalar(select(func.count()).select_from(resolved_sub))

    escalated_sub = base.where(Ticket.status == TicketStatus.escalated).subquery()
    escalated_count = await db.scalar(select(func.count()).select_from(escalated_sub))

    avg_hours = await db.scalar(
        select(
            func.avg(func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600.0)
        )
        .join(Class, Ticket.class_id == Class.id)
        .join(Filiere, Class.filiere_id == Filiere.id)
        .where(Filiere.school_id == school_id, Ticket.resolved_at.is_not(None))
    )

    cat_rows = await db.execute(
        select(Ticket.category, func.count())
        .join(Class, Ticket.class_id == Class.id)
        .join(Filiere, Class.filiere_id == Filiere.id)
        .where(Filiere.school_id == school_id, Ticket.category.is_not(None))
        .group_by(Ticket.category)
    )
    by_cat = {c.value: 0 for c in TicketCategory}
    for row in cat_rows.all():
        cat, cnt = row[0], row[1]
        if cat is not None:
            by_cat[cat.value] = int(cnt)

    return {
        "total_tickets": int(total or 0),
        "open_tickets": int(open_count or 0),
        "resolved_tickets": int(resolved_count or 0),
        "escalated_tickets": int(escalated_count or 0),
        "avg_resolution_hours": float(avg_hours) if avg_hours is not None else 0.0,
        "tickets_by_category": by_cat,
    }


async def get_filiere_stats(db: AsyncSession, filiere_id: uuid.UUID) -> dict:
    filiere = await db.get(Filiere, filiere_id)
    if not filiere:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filiere not found")

    classes_result = await db.scalars(select(Class).where(Class.filiere_id == filiere_id))
    classes = list(classes_result.all())
    out: list[dict] = []

    for cls in classes:
        total = await db.scalar(select(func.count()).select_from(Ticket).where(Ticket.class_id == cls.id))
        open_c = await db.scalar(
            select(func.count())
            .select_from(Ticket)
            .where(
                Ticket.class_id == cls.id,
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]),
            )
        )
        cats = await db.execute(
            select(Ticket.category, func.count())
            .where(Ticket.class_id == cls.id, Ticket.category.is_not(None))
            .group_by(Ticket.category)
        )
        top_cat = None
        best = 0
        for row in cats.all():
            cat, cnt = row[0], row[1]
            if cnt > best:
                best = cnt
                top_cat = cat.value

        out.append(
            {
                "class_name": cls.name,
                "total_tickets": int(total or 0),
                "open_tickets": int(open_c or 0),
                "top_category": top_cat,
            }
        )

    return {"classes": out}


async def get_class_patterns(db: AsyncSession, class_id: uuid.UUID) -> dict:
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    groups_result = await db.scalars(
        select(AggregationGroup)
        .where(AggregationGroup.class_id == class_id)
        .order_by(AggregationGroup.last_seen.desc())
    )
    groups = list(groups_result.all())
    total_students = await db.scalar(
        select(func.count()).select_from(Student).where(Student.class_id == class_id)
    )
    active = await db.scalar(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.class_id == class_id,
            Ticket.status.in_(
                [TicketStatus.open, TicketStatus.in_progress, TicketStatus.escalated]
            ),
        )
    )

    return {
        "aggregation_groups": [
            {
                "pattern_key": g.pattern_key,
                "count": g.count,
                "last_seen": g.last_seen.isoformat() if g.last_seen else None,
                "category": g.category,
            }
            for g in groups
        ],
        "total_students": int(total_students or 0),
        "active_tickets": int(active or 0),
    }


async def get_ticket_trends(db: AsyncSession, school_id: uuid.UUID, days: int = 30) -> list[dict]:
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    if days < 1:
        days = 1
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days - 1)
    start_dt = datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc)

    created_day = func.date_trunc("day", Ticket.created_at).label("created_day")
    created_rows = await db.execute(
        select(created_day, func.count(Ticket.id).label("cnt"))
        .join(Class, Ticket.class_id == Class.id)
        .join(Filiere, Class.filiere_id == Filiere.id)
        .where(Filiere.school_id == school_id, Ticket.created_at >= start_dt)
        .group_by(created_day)
    )
    created_map: dict[date, int] = {}
    for row in created_rows.all():
        d, cnt = row[0], row[1]
        if d is not None:
            day = d.date() if isinstance(d, datetime) else d
            created_map[day] = int(cnt)

    resolved_day = func.date_trunc("day", Ticket.resolved_at).label("resolved_day")
    resolved_rows = await db.execute(
        select(resolved_day, func.count(Ticket.id).label("cnt"))
        .join(Class, Ticket.class_id == Class.id)
        .join(Filiere, Class.filiere_id == Filiere.id)
        .where(
            Filiere.school_id == school_id,
            Ticket.resolved_at.is_not(None),
            Ticket.resolved_at >= start_dt,
        )
        .group_by(resolved_day)
    )
    resolved_map: dict[date, int] = {}
    for row in resolved_rows.all():
        d, cnt = row[0], row[1]
        if d is not None:
            day = d.date() if isinstance(d, datetime) else d
            resolved_map[day] = int(cnt)

    out: list[dict] = []
    current = start
    while current <= end:
        out.append(
            {
                "date": current.isoformat(),
                "created_count": created_map.get(current, 0),
                "resolved_count": resolved_map.get(current, 0),
            }
        )
        current += timedelta(days=1)
    return out


async def get_top_issues(db: AsyncSession, school_id: uuid.UUID, limit: int = 10) -> list[dict]:
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    rows = await db.execute(
        select(
            AggregationGroup.pattern_key,
            AggregationGroup.count,
            AggregationGroup.category,
            Class.name,
        )
        .join(Class, AggregationGroup.class_id == Class.id)
        .join(Filiere, Class.filiere_id == Filiere.id)
        .where(Filiere.school_id == school_id)
        .order_by(AggregationGroup.count.desc())
        .limit(limit)
    )
    return [
        {
            "pattern_key": r[0],
            "count": r[1],
            "category": r[2],
            "class_name": r[3],
        }
        for r in rows.all()
    ]
