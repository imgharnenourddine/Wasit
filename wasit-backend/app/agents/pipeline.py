from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.aggregator import aggregate_problem
from app.agents.broadcast import broadcast_result
from app.agents.classifier import classify_problem
from app.agents.router import route_destination
from app.agents.state import AgentState
from app.agents.summary import build_summary
from app.services.agent_persist import persist_agent_outputs


async def run_agent_pipeline(state: AgentState, db: AsyncSession) -> AgentState:
    state = await classify_problem(state)
    state = await aggregate_problem(state, db)
    state = route_destination(state)
    await persist_agent_outputs(db, UUID(state["ticket_id"]), state)
    if state.get("category") == "emergency":
        return await broadcast_result(state, db)
    state = await build_summary(state)
    return await broadcast_result(state, db)
