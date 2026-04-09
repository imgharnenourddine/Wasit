import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.delegate_data import AIDelegateConfig, FilierePDFDocument
    from app.models.problem import AggregationGroup
    from app.models.student import ProjectGroup, Student
    from app.models.ticket import Ticket
    from app.models.user import User


class School(Base):
    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    filieres: Mapped[list["Filiere"]] = relationship(
        back_populates="school", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"School(id={self.id}, name={self.name}, domain={self.domain})"


class Filiere(Base):
    __tablename__ = "filieres"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    responsible_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    aggregation_poll_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    school: Mapped["School"] = relationship(back_populates="filieres")
    responsible: Mapped["User | None"] = relationship(
        "User", back_populates="responsible_filieres", foreign_keys=[responsible_id]
    )
    classes: Mapped[list["Class"]] = relationship(
        back_populates="filiere", cascade="all, delete-orphan", passive_deletes=True
    )
    pdf_documents: Mapped[list["FilierePDFDocument"]] = relationship(
        "FilierePDFDocument",
        back_populates="filiere",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Filiere(id={self.id}, name={self.name}, school_id={self.school_id})"


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filiere_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filieres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(30), nullable=False)
    delegate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    filiere: Mapped["Filiere"] = relationship(back_populates="classes")
    delegate: Mapped["User | None"] = relationship(
        "User", back_populates="delegated_classes", foreign_keys=[delegate_id]
    )
    students: Mapped[list["Student"]] = relationship(
        back_populates="class_", cascade="all, delete-orphan", passive_deletes=True
    )
    project_groups: Mapped[list["ProjectGroup"]] = relationship(
        back_populates="class_", cascade="all, delete-orphan", passive_deletes=True
    )
    tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="class_", cascade="all, delete-orphan", passive_deletes=True
    )
    aggregation_groups: Mapped[list["AggregationGroup"]] = relationship(
        back_populates="class_", cascade="all, delete-orphan", passive_deletes=True
    )
    ai_delegate_config: Mapped["AIDelegateConfig | None"] = relationship(
        "AIDelegateConfig",
        back_populates="class_",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"Class(id={self.id}, name={self.name}, academic_year={self.academic_year})"
