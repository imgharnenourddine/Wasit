import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.institution import Class
    from app.models.ticket import Ticket


class AggregationGroup(Base):
    __tablename__ = "aggregation_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pattern_key: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    class_: Mapped["Class"] = relationship(back_populates="aggregation_groups")
    problems: Mapped[list["Problem"]] = relationship(
        back_populates="aggregation_group", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"AggregationGroup(id={self.id}, class_id={self.class_id}, pattern_key={self.pattern_key})"


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    language_detected: Mapped[str | None] = mapped_column(String(50), nullable=True)
    classified_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    aggregation_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("aggregation_groups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="problems")
    aggregation_group: Mapped["AggregationGroup | None"] = relationship(back_populates="problems")

    def __repr__(self) -> str:
        return f"Problem(id={self.id}, ticket_id={self.ticket_id}, category={self.classified_category})"
