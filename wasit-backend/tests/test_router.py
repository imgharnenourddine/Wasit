"""Unit tests for rule-based routing (no I/O)."""

from app.agents.router import route_destination
from app.agents.state import AgentState


def test_route_emergency() -> None:
    s: AgentState = {"category": "emergency", "similar_count": 0}
    route_destination(s)
    assert s["destination"] == "emergency"


def test_route_personal() -> None:
    s: AgentState = {"category": "personal", "similar_count": 0}
    route_destination(s)
    assert s["destination"] == "listening"


def test_route_academic_high_similarity_to_teacher() -> None:
    s: AgentState = {"category": "academic", "similar_count": 3}
    route_destination(s)
    assert s["destination"] == "teacher"


def test_route_academic_low_similarity_to_delegate() -> None:
    s: AgentState = {"category": "academic", "similar_count": 2}
    route_destination(s)
    assert s["destination"] == "delegate"


def test_route_administrative_to_admin() -> None:
    s: AgentState = {"category": "administrative", "similar_count": 0}
    route_destination(s)
    assert s["destination"] == "admin"
