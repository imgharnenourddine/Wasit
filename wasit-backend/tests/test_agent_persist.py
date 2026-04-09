"""Persist agent outputs onto ORM rows (in-memory SQLite)."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.state import AgentState
from app.core.database import Base
from app.models.institution import Class, Filiere, School
from app.models.problem import Problem
from app.models.student import Student
from app.models.ticket import Ticket, TicketCategory, TicketPriority, TicketStatus
from app.models.user import Role, User
from app.services.agent_persist import persist_agent_outputs


@pytest_asyncio.fixture
async def memory_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_persist_updates_ticket_and_problem(memory_session: AsyncSession) -> None:
    db = memory_session
    school = School(name="Test School", domain="test.edu")
    db.add(school)
    await db.flush()

    filiere = Filiere(name="Info", school_id=school.id)
    db.add(filiere)
    await db.flush()

    cls = Class(name="1A", filiere_id=filiere.id, academic_year="2025-2026")
    db.add(cls)
    await db.flush()

    user = User(
        email="st@example.com",
        hashed_password="x",
        role=Role.student,
        first_name="A",
        last_name="B",
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
        title="t",
        description="hello",
        status=TicketStatus.open,
        priority=TicketPriority.medium,
        category=TicketCategory.administrative,
    )
    db.add(ticket)
    await db.flush()

    prob = Problem(ticket_id=ticket.id, raw_text="hello")
    db.add(prob)
    await db.commit()

    tid = ticket.id
    state: AgentState = {
        "category": "personal",
        "priority": "urgent",
        "language": "en",
        "raw_text": "hello",
    }
    await persist_agent_outputs(db, tid, state)

    await db.refresh(ticket)
    await db.refresh(prob)
    assert ticket.category == TicketCategory.personal
    assert ticket.priority == TicketPriority.urgent
    assert prob.language_detected == "en"
    assert prob.classified_category == "personal"
