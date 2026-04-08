import json

import httpx
from langdetect import detect

from app.agents.state import AgentState
from app.core.config import settings

CLASSIFIER_SYSTEM_PROMPT = (
    "You are a classifier for university student problems. "
    "Classify the problem into: category (academic/administrative/personal/emergency) "
    "and priority (low/medium/high/urgent/emergency). "
    "Respond ONLY with JSON: {category, priority, language}"
)


class ClassifierAgent:
    def __init__(self) -> None:
        self.api_key = settings.MISTRAL_API_KEY
        self.model = "mistral-large-latest"

    async def run(self, state: AgentState) -> AgentState:
        raw_text = state.get("raw_text", "")
        try:
            detected_language = detect(raw_text) if raw_text.strip() else "unknown"
        except Exception:
            detected_language = "unknown"

        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            body = response.json()
        response_text = body["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            state["error"] = "Classifier response is not valid JSON"
            return state

        state["language"] = str(parsed.get("language") or detected_language)
        state["category"] = str(parsed.get("category") or "academic")
        state["priority"] = str(parsed.get("priority") or "low")
        return state
