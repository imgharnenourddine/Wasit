import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.institution import Class
    from app.models.problem import Problem
    from app.models.student import Student
    from app.models.user import User


class TicketStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    escalated = "escalated"
    resolved = "resolved"
    closed = "closed"


class TicketPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"
    emergency = "emergency"


class TicketCategory(str, enum.Enum):
    academic = "academic"
    administrative = "administrative"
    personal = "personal"
    emergency = "emergency"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_status_enum"), default=TicketStatus.open, nullable=False
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, name="ticket_priority_enum"), default=TicketPriority.low, nullable=False
    )
    category: Mapped[TicketCategory | None] = mapped_column(
        Enum(TicketCategory, name="ticket_category_enum"), nullable=True
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped["Student"] = relationship(back_populates="tickets")
    class_: Mapped["Class"] = relationship(back_populates="tickets")
    assignee: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_tickets", foreign_keys=[assigned_to]
    )
    history: Mapped[list["TicketHistory"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True
    )
    problems: Mapped[list["Problem"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"Ticket(id={self.id}, status={self.status.value}, priority={self.priority.value})"


class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_history_old_status_enum"), nullable=False
    )
    new_status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, name="ticket_history_new_status_enum"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="history")
    changed_by_user: Mapped["User"] = relationship(
        "User", back_populates="history_changes", foreign_keys=[changed_by]
    )

    def __repr__(self) -> str:
        return f"TicketHistory(id={self.id}, ticket_id={self.ticket_id}, new_status={self.new_status.value})"
