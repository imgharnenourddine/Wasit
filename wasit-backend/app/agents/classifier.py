from app.agents.state import AgentState
from app.agents.openrouter_client import chat_json


async def classify_problem(state: AgentState) -> AgentState:
    text = state.get("raw_text", "").lower()

    category = "administrative"
    priority = "medium"
    language = "unknown"

    try:
        result = await chat_json(
            system_prompt=(
                "You classify university student problems. "
                "Return strict JSON only: "
                '{"category":"academic|administrative|personal|emergency",'
                '"priority":"low|medium|high|urgent|emergency","language":"string"}'
            ),
            user_prompt=f"Problem text:\n{text}",
        )
        category = str(result.get("category", category))
        priority = str(result.get("priority", priority))
        language = str(result.get("language", language))
    except Exception:
        if any(word in text for word in ["urgent", "danger", "violence", "suicide", "fire"]):
            category = "emergency"
            priority = "emergency"
        elif any(word in text for word in ["stress", "anxiety", "depressed", "harassment"]):
            category = "personal"
            priority = "high"
        elif any(word in text for word in ["exam", "course", "teacher", "grade", "module"]):
            category = "academic"
            priority = "medium"

        if any(word in text for word in ["le", "la", "de", "et", "bonjour"]):
            language = "fr"
        elif any(word in text for word in ["the", "and", "hello"]):
            language = "en"

    state["category"] = category
    state["priority"] = priority
    state["language"] = language
    return state
