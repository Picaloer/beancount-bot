"""add import stages and summaries

Revision ID: 007
Revises: 006
Create Date: 2026-03-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "import_stages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("import_id", sa.String(length=36), sa.ForeignKey("bill_imports.id"), nullable=False),
        sa.Column("stage_key", sa.String(length=50), nullable=False),
        sa.Column("stage_label", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("import_id", "stage_key", name="uq_import_stage_import_stage_key"),
    )
    op.create_index("ix_import_stages_import_id", "import_stages", ["import_id"])

    op.create_table(
        "import_summaries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("import_id", sa.String(length=36), sa.ForeignKey("bill_imports.id"), nullable=False, unique=True),
        sa.Column("inserted_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("beancount_entry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rule_based_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_based_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fallback_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_confidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("import_summaries")
    op.drop_index("ix_import_stages_import_id", table_name="import_stages")
    op.drop_table("import_stages")
