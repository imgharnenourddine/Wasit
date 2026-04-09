"""Replace timetable_slots and exam_events with filiere_pdf_documents.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-09

Changes:
 - DROP TABLE timetable_slots
 - DROP TABLE exam_events
 - CREATE TABLE filiere_pdf_documents
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old structured tables (data is in an external system; we use PDFs now)
    op.drop_index(op.f("ix_exam_events_starts_at"), table_name="exam_events")
    op.drop_index(op.f("ix_exam_events_class_id"), table_name="exam_events")
    op.drop_table("exam_events")

    op.drop_index(op.f("ix_timetable_slots_class_id"), table_name="timetable_slots")
    op.drop_table("timetable_slots")

    # Create the new PDF document store (one per filière × doc_type)
    op.create_table(
        "filiere_pdf_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filiere_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", sa.String(length=50), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("cloudinary_url", sa.Text(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["filiere_id"], ["filieres.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_filiere_pdf_documents_filiere_id"),
        "filiere_pdf_documents",
        ["filiere_id"],
        unique=False,
    )


def downgrade() -> None:
    # Remove pdf documents table
    op.drop_index(
        op.f("ix_filiere_pdf_documents_filiere_id"), table_name="filiere_pdf_documents"
    )
    op.drop_table("filiere_pdf_documents")

    # Restore timetable_slots
    op.create_table(
        "timetable_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("room", sa.String(length=100), nullable=True),
        sa.Column("teacher_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_timetable_slots_class_id"), "timetable_slots", ["class_id"], unique=False
    )

    # Restore exam_events
    op.create_table(
        "exam_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("room", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exam_events_class_id"), "exam_events", ["class_id"], unique=False)
    op.create_index(op.f("ix_exam_events_starts_at"), "exam_events", ["starts_at"], unique=False)
