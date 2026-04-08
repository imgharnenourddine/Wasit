import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class School(Base):
    __tablename__ = "schools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    filieres = relationship("Filiere", back_populates="school", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"School(id={self.id}, name={self.name})"


class Filiere(Base):
    __tablename__ = "filieres"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    responsible_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    school = relationship("School", back_populates="filieres")
    responsible = relationship("User", back_populates="responsible_filieres", foreign_keys=[responsible_id])
    classes = relationship("Class", back_populates="filiere", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Filiere(id={self.id}, name={self.name}, school_id={self.school_id})"


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filiere_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filieres.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(30), nullable=False)
    delegate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    filiere = relationship("Filiere", back_populates="classes")
    delegate = relationship("User", back_populates="delegated_classes", foreign_keys=[delegate_id])
    students = relationship("Student", back_populates="class_", cascade="all, delete-orphan")
    project_groups = relationship("ProjectGroup", back_populates="class_", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Class(id={self.id}, name={self.name}, year={self.academic_year})"
