from typing import TypedDict


class AgentState(TypedDict, total=False):
    raw_text: str
    language: str
    category: str
    priority: str
    aggregation_group_id: str | None
    similar_count: int
    destination: str
    structured_summary: str
    ticket_id: str
    class_id: str
    student_id: str
    telegram_sent: bool
    error: str | None
