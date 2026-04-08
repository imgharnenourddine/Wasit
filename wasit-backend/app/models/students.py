import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    student_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    user = relationship("User", back_populates="student_profile")
    class_ = relationship("Class", back_populates="students")
    group_memberships = relationship(
        "ProjectGroupMember", back_populates="student", cascade="all, delete-orphan"
    )
    tickets = relationship("Ticket", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Student(id={self.id}, user_id={self.user_id}, class_id={self.class_id})"


class ProjectGroup(Base):
    __tablename__ = "project_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    class_ = relationship("Class", back_populates="project_groups")
    members = relationship("ProjectGroupMember", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"ProjectGroup(id={self.id}, class_id={self.class_id}, name={self.name})"


class ProjectGroupMember(Base):
    __tablename__ = "project_group_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )

    group = relationship("ProjectGroup", back_populates="members")
    student = relationship("Student", back_populates="group_memberships")

    def __repr__(self) -> str:
        return f"ProjectGroupMember(id={self.id}, group_id={self.group_id}, student_id={self.student_id})"
