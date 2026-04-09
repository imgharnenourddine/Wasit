from typing import Any
from uuid import UUID

from app.agents.pipeline import run_agent_pipeline
from app.agents.state import AgentState
from app.core.database import SessionLocal


async def run_pipeline(ticket_id: UUID, class_id: UUID, student_id: UUID, raw_text: str) -> dict[str, Any]:
    state: AgentState = {
        "ticket_id": str(ticket_id),
        "class_id": str(class_id),
        "student_id": str(student_id),
        "raw_text": raw_text,
        "telegram_sent": False,
    }
    async with SessionLocal() as db:
        try:
            state = await run_agent_pipeline(state, db)
            state["status"] = "ok"
        except Exception as exc:  # pragma: no cover - defensive integration guard
            state["status"] = "failed"
            state["error"] = str(exc)
    return state
