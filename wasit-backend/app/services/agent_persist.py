"""Persist classifier/router outputs onto Ticket and Problem before broadcast (single import target)."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.models.problem import Problem
from app.models.ticket import Ticket, TicketCategory, TicketPriority

_CAT: dict[str, TicketCategory] = {
    "academic": TicketCategory.academic,
    "administrative": TicketCategory.administrative,
    "personal": TicketCategory.personal,
    "emergency": TicketCategory.emergency,
}

_PRI: dict[str, TicketPriority] = {
    "low": TicketPriority.low,
    "medium": TicketPriority.medium,
    "high": TicketPriority.high,
    "urgent": TicketPriority.urgent,
    "emergency": TicketPriority.emergency,
}


async def persist_agent_outputs(db: AsyncSession, ticket_id: UUID, state: AgentState) -> None:
    ticket = await db.get(Ticket, ticket_id)
    if not ticket:
        return
    cat_s = (state.get("category") or "").lower()
    pr_s = (state.get("priority") or "").lower()
    if cat_s in _CAT:
        ticket.category = _CAT[cat_s]
    if pr_s in _PRI:
        ticket.priority = _PRI[pr_s]

    prob_q = await db.execute(select(Problem).where(Problem.ticket_id == ticket_id))
    prob = prob_q.scalar_one_or_none()
    if prob:
        lang = state.get("language")
        if lang:
            prob.language_detected = lang
        cs = state.get("category")
        if cs:
            prob.classified_category = cs
            prob.category = cs
    await db.commit()
