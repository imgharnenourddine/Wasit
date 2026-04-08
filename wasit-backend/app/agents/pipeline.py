from app.agents.aggregator import aggregate_problem
from app.agents.broadcast import broadcast_result
from app.agents.classifier import classify_problem
from app.agents.router import route_destination
from app.agents.state import AgentState
from app.agents.summary import build_summary


async def run_agent_pipeline(state: AgentState) -> AgentState:
    state = await classify_problem(state)
    state = await aggregate_problem(state)
    state = route_destination(state)
    if state.get("category") == "emergency":
        return await broadcast_result(state)
    state = await build_summary(state)
    state = await broadcast_result(state)
    return state
