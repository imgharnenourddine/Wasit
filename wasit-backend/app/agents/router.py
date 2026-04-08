from app.agents.state import AgentState


def route_destination(state: AgentState) -> AgentState:
    category = state.get("category", "administrative")
    similar_count = int(state.get("similar_count", 0))

    if category == "emergency":
        destination = "emergency"
    elif category == "personal":
        destination = "listening"
    elif category == "academic":
        destination = "teacher" if similar_count >= 3 else "delegate"
    else:
        destination = "admin"

    state["destination"] = destination
    return state
