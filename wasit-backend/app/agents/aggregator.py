from app.agents.state import AgentState
from app.agents.openrouter_client import chat_json


async def aggregate_problem(state: AgentState) -> AgentState:
    category = state.get("category", "administrative")
    class_id = state.get("class_id", "unknown-class")
    raw_text = state.get("raw_text", "")
    pattern_key = f"{class_id}:{category}"
    similar_count = 1

    try:
        result = await chat_json(
            system_prompt=(
                "You generate a short grouping key for student issues. "
                'Return strict JSON only: {"pattern_key":"short_snake_case_key"}'
            ),
            user_prompt=(
                f"Class id: {class_id}\n"
                f"Category: {category}\n"
                f"Problem: {raw_text}\n"
                "Generate a concise stable pattern key."
            ),
        )
        key = str(result.get("pattern_key", "")).strip().replace(" ", "_")
        if key:
            pattern_key = f"{class_id}:{key}"
    except Exception:
        pass

    state["aggregation_group_id"] = pattern_key
    state["similar_count"] = similar_count
    return state
