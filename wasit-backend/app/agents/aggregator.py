import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.state import AgentState
from app.core.config import settings
from app.models.agents import AggregationGroup, Problem

AGGREGATOR_SYSTEM_PROMPT = (
    "Given this new problem: [text]. Given these existing problem groups: [list]. "
    "Does this belong to an existing group? Respond ONLY with JSON: "
    "{group_id: string_or_null, is_new_group: bool, pattern_key: string}"
)


class AggregatorAgent:
    def __init__(self) -> None:
        self.api_key = settings.MISTRAL_API_KEY
        self.model = "mistral-large-latest"

    async def run(self, state: AgentState, db: AsyncSession) -> AgentState:
        class_id = uuid.UUID(state["class_id"])
        ticket_id = uuid.UUID(state["ticket_id"])
        student_id = uuid.UUID(state["student_id"])
        category = state["category"]
        raw_text = state["raw_text"]

        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        groups_result = await db.scalars(
            select(AggregationGroup).where(
                AggregationGroup.class_id == class_id,
                AggregationGroup.category == category,
                AggregationGroup.last_seen >= cutoff,
            )
        )
        groups = list(groups_result.all())
        groups_payload = [
            {
                "id": str(group.id),
                "pattern_key": group.pattern_key,
                "count": group.count,
                "last_seen": group.last_seen.isoformat() if group.last_seen else None,
            }
            for group in groups
        ]

        prompt = (
            f"Given this new problem: {raw_text}\n\n"
            f"Given these existing problem groups: {json.dumps(groups_payload)}"
        )
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": AGGREGATOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions", json=payload, headers=headers
            )
            response.raise_for_status()
            body = response.json()
        response_text = body["choices"][0]["message"]["content"]

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            state["error"] = "Aggregator response is not valid JSON"
            return state

        is_new_group = bool(parsed.get("is_new_group", True))
        group_id_value = parsed.get("group_id")
        pattern_key = str(parsed.get("pattern_key") or raw_text[:120])

        target_group: AggregationGroup | None = None
        if not is_new_group and group_id_value:
            try:
                group_uuid = uuid.UUID(str(group_id_value))
                target_group = await db.get(AggregationGroup, group_uuid)
            except ValueError:
                target_group = None

        if target_group is None:
            target_group = AggregationGroup(
                class_id=class_id,
                category=category,
                pattern_key=pattern_key,
                count=1,
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
            )
            db.add(target_group)
            await db.flush()
        else:
            target_group.count += 1
            target_group.last_seen = datetime.now(timezone.utc)

        existing = await db.scalar(select(Problem).where(Problem.ticket_id == ticket_id))
        if existing is not None:
            existing.class_id = class_id
            existing.student_id = student_id
            existing.category = category
            existing.aggregation_group_id = target_group.id
        else:
            db.add(
                Problem(
                    ticket_id=ticket_id,
                    class_id=class_id,
                    student_id=student_id,
                    raw_text=raw_text,
                    category=category,
                    aggregation_group_id=target_group.id,
                )
            )
        await db.commit()
        await db.refresh(target_group)

        state["aggregation_group_id"] = str(target_group.id)
        state["similar_count"] = int(target_group.count)
        return state


_aggregator = AggregatorAgent()


async def aggregate_problem(state: AgentState) -> AgentState:
    from app.core.database import SessionLocal

    async with SessionLocal() as db:
        return await _aggregator.run(state, db)
