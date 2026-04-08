from app.agents.state import AgentState
from app.services.notifications import notify_destination
from app.services.telegram import send_to_group


async def broadcast_result(state: AgentState) -> AgentState:
    destination = state.get("destination", "admin")
    ticket_id = state.get("ticket_id", "")
    class_id = state.get("class_id", "")
    summary = state.get("structured_summary", "No summary provided")

    await notify_destination(destination=destination, summary=summary, ticket_id=ticket_id)

    if destination == "teacher":
        await send_to_group(class_id=class_id, message=summary)
        state["telegram_sent"] = True
    else:
        state["telegram_sent"] = False

    return state
