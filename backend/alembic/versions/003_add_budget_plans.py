"""add budget plans

Revision ID: 003
Revises: 002
Create Date: 2026-03-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "budget_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("year_month", sa.String(length=7), nullable=False),
        sa.Column("category_l1", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("spent", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("usage_ratio", sa.Numeric(8, 4), nullable=False, server_default="0"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="ai"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "year_month", "category_l1", name="uq_budget_plan_user_month_category"),
    )
    op.create_index("ix_budget_plans_user_month", "budget_plans", ["user_id", "year_month"])


def downgrade() -> None:
    op.drop_index("ix_budget_plans_user_month", table_name="budget_plans")
    op.drop_table("budget_plans")
