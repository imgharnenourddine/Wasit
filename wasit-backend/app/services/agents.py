from typing import Any

from app.agents.aggregator import aggregate_problem
from app.agents.broadcast import broadcast_result
from app.agents.classifier import classify_problem
from app.agents.router import route_destination
from app.agents.state import AgentState
from app.agents.summary import build_summary


async def run_pipeline(ticket_id: str, class_id: str, student_id: str, raw_text: str) -> dict[str, Any]:
    state: AgentState = {
        "ticket_id": ticket_id,
        "class_id": class_id,
        "student_id": student_id,
        "raw_text": raw_text,
        "telegram_sent": False,
    }
    try:
        state = await classify_problem(state)
        state = await aggregate_problem(state)
        state = route_destination(state)
        state = await build_summary(state)
        state = await broadcast_result(state)
        state["status"] = "ok"
    except Exception as exc:  # pragma: no cover - defensive integration guard
        state["status"] = "failed"
        state["error"] = str(exc)
    return state
