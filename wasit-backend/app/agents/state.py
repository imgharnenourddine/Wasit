from typing import Literal, TypedDict


CategoryType = Literal["academic", "administrative", "personal", "emergency"]
PriorityType = Literal["low", "medium", "high", "urgent", "emergency"]
DestinationType = Literal["teacher", "admin", "listening", "emergency", "delegate"]


class AgentState(TypedDict):
    raw_text: str
    language: str
    category: CategoryType
    priority: PriorityType
    aggregation_group_id: str | None
    similar_count: int
    destination: DestinationType
    structured_summary: str
    ticket_id: str
    class_id: str
    student_id: str
    error: str | None
