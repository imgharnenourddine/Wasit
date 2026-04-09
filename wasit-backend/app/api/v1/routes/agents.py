"""API routes for agent pipeline (debug / dry-run)."""

from uuid import uuid4

from fastapi import APIRouter, Depends

from app.agents.classifier import classify_problem
from app.agents.router import route_destination
from app.agents.state import AgentState
from app.agents.summary import build_summary
from app.core.dependencies import require_role
from app.models.user import User
from app.schemas.agents import AgentDryRunRequest

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/dry-run")
async def agents_dry_run(
    payload: AgentDryRunRequest,
    _: User = Depends(require_role("admin")),
) -> dict:
    """
    Run classifier → router → summary without aggregation or broadcast.
    Does not write to the database. Use for prompt/API key checks.
    """
    state: AgentState = {
        "ticket_id": str(uuid4()),
        "class_id": str(payload.class_id),
        "student_id": str(payload.student_id),
        "raw_text": payload.raw_text,
        "telegram_sent": False,
    }
    state = await classify_problem(state)
    state = route_destination(state)
    if state.get("category") == "emergency":
        raw = state.get("raw_text", "")
        state["structured_summary"] = (
            f"[EMERGENCY] {state.get('priority', '?')} — {raw[:500]}"
        )
        return {"mode": "dry_run_emergency", "agent_state": state}
    state = await build_summary(state)
    return {"mode": "dry_run", "agent_state": state}
