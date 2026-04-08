from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.ticket import TicketCategory, TicketPriority, TicketStatus


class ProblemSubmit(BaseModel):
    raw_text: str = Field(min_length=5, max_length=4000)


class TicketUpdate(BaseModel):
    status: TicketStatus
    note: str | None = Field(default=None, max_length=2000)


class TicketHistoryResponse(BaseModel):
    old_status: TicketStatus | None
    new_status: TicketStatus
    note: str | None
    changed_by: UUID
    created_at: datetime


class TicketResponse(BaseModel):
    id: UUID
    title: str | None
    description: str
    category: TicketCategory | None
    priority: TicketPriority
    status: TicketStatus
    assigned_to: UUID | None
    student_id: UUID
    class_id: UUID
    created_at: datetime
    updated_at: datetime
    history: list[TicketHistoryResponse] = []
