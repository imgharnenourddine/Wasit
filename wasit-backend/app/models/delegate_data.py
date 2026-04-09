"""AI Delegate helper data: per-class bot config, filière PDF documents (FEATURE_AI_DELEGATE)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AIDelegateConfig(Base):
    __tablename__ = "ai_delegate_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    personality_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    class_: Mapped["Class"] = relationship("Class", back_populates="ai_delegate_config")  # noqa: F821


class FilierePDFDocument(Base):
    """Stores a parsed PDF (timetable or exam schedule) uploaded by the chef de filière.

    The external scheduling system produces PDFs; we extract their text and feed it to
    the AI delegate bot via LangChain RAG rather than storing structured rows.
    """

    __tablename__ = "filiere_pdf_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filiere_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filieres.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "timetable" | "exam_schedule"
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Full text extracted from the PDF by PyMuPDF
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Original file stored on Cloudinary (resource_type=raw)
    cloudinary_url: Mapped[str] = mapped_column(Text, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    filiere: Mapped["Filiere"] = relationship("Filiere", back_populates="pdf_documents")  # noqa: F821
