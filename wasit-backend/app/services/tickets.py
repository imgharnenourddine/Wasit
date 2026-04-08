from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.problem import Problem
from app.models.ticket import Ticket, TicketCategory, TicketHistory, TicketPriority, TicketStatus
from app.services.agents import run_pipeline


def _make_title(raw_text: str) -> str:
    compact = " ".join(raw_text.strip().split())
    return compact[:120] if compact else "New ticket"


async def create_ticket_from_problem(
    db: AsyncSession, student_id: str, class_id: str, raw_text: str
) -> Ticket:
    ticket = Ticket(
        student_id=student_id,
        class_id=class_id,
        title=_make_title(raw_text),
        description=raw_text,
        status=TicketStatus.open,
        priority=TicketPriority.medium,
        category=TicketCategory.administrative,
    )
    db.add(ticket)
    await db.flush()

    db.add(Problem(ticket_id=ticket.id, raw_text=raw_text))
    db.add(
        TicketHistory(
            ticket_id=ticket.id,
            changed_by=student_id,
            old_status=None,
            new_status=TicketStatus.open,
            note="Ticket created",
        )
    )
    await db.commit()
    await db.refresh(ticket)

    # Non-blocking bridge: pipeline may still be incomplete during development.
    await run_pipeline(ticket_id=ticket.id, class_id=class_id, student_id=student_id, raw_text=raw_text)
    return ticket


async def get_ticket(db: AsyncSession, ticket_id: str) -> tuple[Ticket, list[TicketHistory]]:
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    history_q = await db.execute(
        select(TicketHistory).where(TicketHistory.ticket_id == ticket_id).order_by(TicketHistory.created_at.asc())
    )
    history = list(history_q.scalars().all())
    return ticket, history


async def get_student_tickets(db: AsyncSession, student_id: str) -> list[Ticket]:
    result = await db.execute(
        select(Ticket).where(Ticket.student_id == student_id).order_by(Ticket.created_at.desc())
    )
    return list(result.scalars().all())


async def get_class_tickets(
    db: AsyncSession, class_id: str, status_filter: TicketStatus | None = None
) -> list[Ticket]:
    stmt = select(Ticket).where(Ticket.class_id == class_id)
    if status_filter:
        stmt = stmt.where(Ticket.status == status_filter)
    stmt = stmt.order_by(Ticket.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_all_open_tickets(db: AsyncSession) -> list[Ticket]:
    result = await db.execute(
        select(Ticket).where(
            Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress, TicketStatus.escalated])
        )
        .order_by(Ticket.created_at.desc())
    )
    return list(result.scalars().all())


async def update_ticket_status(
    db: AsyncSession, ticket_id: str, new_status: TicketStatus, changed_by_id: str, note: str | None
) -> Ticket:
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = new_status
    if new_status in (TicketStatus.resolved, TicketStatus.closed):
        ticket.resolved_at = datetime.now(timezone.utc)

    db.add(
        TicketHistory(
            ticket_id=ticket.id,
            changed_by=changed_by_id,
            old_status=old_status,
            new_status=new_status,
            note=note,
        )
    )
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def auto_escalate_overdue_tickets(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    result = await db.execute(
        select(Ticket).where(and_(Ticket.status == TicketStatus.in_progress, Ticket.updated_at <= cutoff))
    )
    overdue = list(result.scalars().all())
    for ticket in overdue:
        ticket.status = TicketStatus.escalated
        db.add(
            TicketHistory(
                ticket_id=ticket.id,
                changed_by="system",
                old_status=TicketStatus.in_progress,
                new_status=TicketStatus.escalated,
                note="Auto-escalated: no response in 48h",
            )
        )
    if overdue:
        await db.commit()
    return len(overdue)
