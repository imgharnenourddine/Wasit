"""AI Delegate config, timetable, exams, filiere poll threshold, user telegram id

Revision ID: a1b2c3d4e5f6
Revises: 6c31492135c4
Create Date: 2026-04-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "6c31492135c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "filieres",
        sa.Column("aggregation_poll_threshold", sa.Integer(), server_default="3", nullable=False),
    )
    op.add_column("users", sa.Column("telegram_user_id", sa.String(length=80), nullable=True))
    op.create_index(op.f("ix_users_telegram_user_id"), "users", ["telegram_user_id"], unique=True)

    op.create_table(
        "ai_delegate_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("personality_prompt", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_delegate_configs_class_id"), "ai_delegate_configs", ["class_id"], unique=True)

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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_timetable_slots_class_id"), "timetable_slots", ["class_id"], unique=False)

    op.create_table(
        "exam_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("class_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("room", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exam_events_class_id"), "exam_events", ["class_id"], unique=False)
    op.create_index(op.f("ix_exam_events_starts_at"), "exam_events", ["starts_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_exam_events_starts_at"), table_name="exam_events")
    op.drop_index(op.f("ix_exam_events_class_id"), table_name="exam_events")
    op.drop_table("exam_events")
    op.drop_index(op.f("ix_timetable_slots_class_id"), table_name="timetable_slots")
    op.drop_table("timetable_slots")
    op.drop_index(op.f("ix_ai_delegate_configs_class_id"), table_name="ai_delegate_configs")
    op.drop_table("ai_delegate_configs")
    op.drop_index(op.f("ix_users_telegram_user_id"), table_name="users")
    op.drop_column("users", "telegram_user_id")
    op.drop_column("filieres", "aggregation_poll_threshold")
