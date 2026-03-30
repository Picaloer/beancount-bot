"""add rule suggestions table

Revision ID: 004
Revises: 003
Create Date: 2026-03-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("category_confidence", sa.Numeric(4, 3), nullable=False, server_default="0"),
    )
    op.create_table(
        "rule_suggestions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("match_field", sa.String(length=20), nullable=False),
        sa.Column("match_value", sa.String(length=255), nullable=False),
        sa.Column("category_l1", sa.String(length=50), nullable=False),
        sa.Column("category_l2", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_transactions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_rule_suggestions_user_status_created",
        "rule_suggestions",
        ["user_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_rule_suggestions_user_status_created", table_name="rule_suggestions")
    op.drop_table("rule_suggestions")
    op.drop_column("transactions", "category_confidence")
