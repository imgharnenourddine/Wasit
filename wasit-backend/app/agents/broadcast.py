from app.agents.state import AgentState
from app.services.notifications import notify_destination


async def broadcast_result(state: AgentState) -> AgentState:
    destination = state.get("destination", "admin")
    ticket_id = state.get("ticket_id", "")
    summary = state.get("structured_summary", "No summary provided")

    await notify_destination(destination=destination, summary=summary, ticket_id=ticket_id)

    # Telegram delivery is handled in telegram service/routes layer to avoid circular imports.
    state["telegram_sent"] = destination == "teacher"

    return state
