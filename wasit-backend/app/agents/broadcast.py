from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.services.notifications import notify_destination


async def broadcast_result(state: AgentState, db: AsyncSession) -> AgentState:
    destination = state.get("destination", "admin")
    ticket_id = state.get("ticket_id", "")
    raw = state.get("raw_text", "")
    summary = state.get("structured_summary")
    if not summary or summary == "No summary provided":
        summary = (
            f"[{str(state.get('priority', '?')).upper()}] "
            f"{state.get('category', 'issue')} (ticket {ticket_id}). {raw[:400]}"
        )

    await notify_destination(destination=destination, summary=summary, ticket_id=ticket_id, db=db)
    return state
