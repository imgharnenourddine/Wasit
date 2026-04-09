"""Classifier: Mistral HTTP mocked via respx."""

import httpx
import pytest
import respx

from app.agents.classifier import classify_problem
from app.agents.state import AgentState


@pytest.mark.asyncio
@respx.mock
async def test_classify_problem_parses_mistral_json() -> None:
    respx.post("https://api.mistral.ai/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"category":"academic","priority":"high","language":"fr"}',
                        }
                    }
                ]
            },
        )
    )
    state: AgentState = {"raw_text": "J ai un problème avec l examen de maths"}
    out = await classify_problem(state)
    assert out.get("category") == "academic"
    assert out.get("priority") == "high"
    assert out.get("language") == "fr"
