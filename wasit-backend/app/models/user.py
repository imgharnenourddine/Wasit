import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.institution import Class, Filiere
    from app.models.student import Student
    from app.models.ticket import Ticket, TicketHistory


class Role(str, enum.Enum):
    student = "student"
    delegate = "delegate"
    teacher = "teacher"
    admin = "admin"
    listening = "listening"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="role_enum"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    student_profile: Mapped["Student | None"] = relationship(back_populates="user", uselist=False)
    delegated_classes: Mapped[list["Class"]] = relationship(
        "Class", back_populates="delegate", foreign_keys="Class.delegate_id"
    )
    responsible_filieres: Mapped[list["Filiere"]] = relationship(
        "Filiere", back_populates="responsible", foreign_keys="Filiere.responsible_id"
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="assignee", foreign_keys="Ticket.assigned_to"
    )
    history_changes: Mapped[list["TicketHistory"]] = relationship(
        "TicketHistory", back_populates="changed_by_user", foreign_keys="TicketHistory.changed_by"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email}, role={self.role.value})"
