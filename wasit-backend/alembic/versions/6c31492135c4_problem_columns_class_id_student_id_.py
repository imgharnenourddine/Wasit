"""Add optional class_id, student_id, category to problems.

Revision ID: 6c31492135c4
Revises:
Create Date: 2026-04-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6c31492135c4"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
    op.create_index("ix_problems_class_id", "problems", ["class_id"], unique=False)
    op.create_index("ix_problems_student_id", "problems", ["student_id"], unique=False)
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


def downgrade() -> None:
    op.drop_constraint("fk_problems_student_id_students", "problems", type_="foreignkey")
    op.drop_constraint("fk_problems_class_id_classes", "problems", type_="foreignkey")
    op.drop_index("ix_problems_student_id", table_name="problems")
    op.drop_index("ix_problems_class_id", table_name="problems")
    op.drop_column("problems", "category")
    op.drop_column("problems", "student_id")
    op.drop_column("problems", "class_id")
