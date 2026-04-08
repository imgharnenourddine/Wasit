from app.agents.state import AgentState
from app.agents.openrouter_client import chat_json


async def build_summary(state: AgentState) -> AgentState:
    destination = state.get("destination", "admin")
    category = state.get("category", "administrative")
    priority = state.get("priority", "medium")
    similar_count = state.get("similar_count", 1)
    raw_text = state.get("raw_text", "")

    fallback = (
        f"[{priority.upper()}] {category} issue for {destination}. "
        f"Similar reports in class: {similar_count}. "
        f"Student message: {raw_text[:300]}"
    )

    try:
        result = await chat_json(
            system_prompt=(
                "You write concise professional summaries for university staff. "
                'Return strict JSON only: {"summary":"..."}'
            ),
            user_prompt=(
                f"Destination: {destination}\n"
                f"Category: {category}\n"
                f"Priority: {priority}\n"
                f"Similar count: {similar_count}\n"
                f"Student message: {raw_text}\n"
                "Write in French. Be actionable and max 120 words."
            ),
        )
        summary = str(result.get("summary", "")).strip()
        state["structured_summary"] = summary or fallback
    except Exception:
        state["structured_summary"] = fallback
    return state
