"""
End-to-end: `run_agent_pipeline` with Mistral + OpenRouter HTTP mocked (respx),
SQLite DB, and notification/Telegram side effects mocked.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio
import respx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.pipeline import run_agent_pipeline
from app.agents.state import AgentState
from app.core.database import Base
from app.models.institution import Class, Filiere, School
from app.models.problem import Problem
from app.models.student import Student
from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus
from app.models.user import Role, User

MISTRAL_CLASSIFIER_BODY = {
    "choices": [
        {
            "message": {
                "content": '{"category":"academic","priority":"medium","language":"en"}',
            }
        }
    ]
}
MISTRAL_AGGREGATOR_BODY = {
    "choices": [
        {
            "message": {
                "content": '{"is_new_group":true,"group_id":null,"pattern_key":"exam_stress"}',
            }
        }
    ]
}
OPENROUTER_BODY = {
    "choices": [
        {
            "message": {
                "content": '{"summary":"Résumé court pour le personnel."}',
            }
        }
    ]
}


@pytest_asyncio.fixture
async def pipeline_db_with_ticket() -> tuple[AsyncSession, Ticket, Class, Student]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as db:
        school = School(name="S", domain="e2e.edu")
        db.add(school)
        await db.flush()

        filiere = Filiere(name="F", school_id=school.id)
        db.add(filiere)
        await db.flush()

        cls = Class(name="C1", filiere_id=filiere.id, academic_year="2025-2026")
        db.add(cls)
        await db.flush()

        user = User(
            email="e2e@example.com",
            hashed_password="x",
            role=Role.student,
            first_name="E",
            last_name="2e",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        student = Student(user_id=user.id, class_id=cls.id)
        db.add(student)
        await db.flush()

        ticket = Ticket(
            student_id=student.id,
            class_id=cls.id,
            title="Exam issue",
            description="I failed the midterm",
            status=TicketStatus.open,
            priority=TicketPriority.medium,
            category=TicketCategory.administrative,
        )
        db.add(ticket)
        await db.flush()

        db.add(Problem(ticket_id=ticket.id, raw_text="I failed the midterm"))
        await db.commit()
        await db.refresh(ticket)
        await db.refresh(cls)
        await db.refresh(student)

        yield db, ticket, cls, student

    await engine.dispose()


@pytest.mark.asyncio
@respx.mock
async def test_run_agent_pipeline_full_mocked_http(
    pipeline_db_with_ticket: tuple[AsyncSession, Ticket, Class, Student],
) -> None:
    db, ticket, cls, student = pipeline_db_with_ticket

    mistral = respx.post("https://api.mistral.ai/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(200, json=MISTRAL_CLASSIFIER_BODY),
            httpx.Response(200, json=MISTRAL_AGGREGATOR_BODY),
        ]
    )
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=OPENROUTER_BODY)
    )

    notify = AsyncMock(return_value={"sent": 1, "destination": "delegate", "ticket_id": str(ticket.id)})

    state: AgentState = {
        "ticket_id": str(ticket.id),
        "class_id": str(cls.id),
        "student_id": str(student.id),
        "raw_text": "I failed the midterm",
    }

    with patch("app.agents.broadcast.notify_destination", notify):
        out = await run_agent_pipeline(state, db)

    assert mistral.called
    assert out.get("category") == "academic"
    assert out.get("destination") == "delegate"
    assert "structured_summary" in out
    assert "Résumé" in (out.get("structured_summary") or "")

    prob = (await db.execute(select(Problem).where(Problem.ticket_id == ticket.id))).scalar_one()
    assert prob.category == "academic"
    assert prob.class_id == cls.id
    assert prob.student_id == student.id

    notify.assert_awaited()
    assert notify.await_args is not None
    call_kw = notify.await_args.kwargs
    assert call_kw.get("db") is db
    assert call_kw.get("destination") == "delegate"
