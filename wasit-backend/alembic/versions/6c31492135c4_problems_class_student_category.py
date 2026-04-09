"""problems: class_id, student_id, category

Revision ID: 6c31492135c4
Revises:
Create Date: 2026-04-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "6c31492135c4"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "problems",
        sa.Column("class_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "problems",
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "problems",
        sa.Column("category", sa.String(length=100), nullable=True),
    )
    op.create_foreign_key(
        "fk_problems_class_id_classes",
        "problems",
        "classes",
        ["class_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_problems_student_id_students",
        "problems",
        "students",
        ["student_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_problems_class_id"), "problems", ["class_id"], unique=False)
    op.create_index(op.f("ix_problems_student_id"), "problems", ["student_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_problems_student_id"), table_name="problems")
    op.drop_index(op.f("ix_problems_class_id"), table_name="problems")
    op.drop_constraint("fk_problems_student_id_students", "problems", type_="foreignkey")
    op.drop_constraint("fk_problems_class_id_classes", "problems", type_="foreignkey")
    op.drop_column("problems", "category")
    op.drop_column("problems", "student_id")
    op.drop_column("problems", "class_id")
