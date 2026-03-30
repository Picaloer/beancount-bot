"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-03-29

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "bill_imports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("file_name", sa.String(255)),
        sa.Column("row_count", sa.Integer(), default=0),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("imported_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("import_id", sa.String(36), sa.ForeignKey("bill_imports.id"), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(10), default="CNY"),
        sa.Column("merchant", sa.String(255), default=""),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("category_l1", sa.String(50), default="其他"),
        sa.Column("category_l2", sa.String(50), nullable=True),
        sa.Column("category_source", sa.String(20), default="fallback"),
        sa.Column("transaction_at", sa.DateTime(), nullable=False),
        sa.Column("raw_data", sa.JSON(), default={}),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_transactions_user_date", "transactions", ["user_id", "transaction_at"])
    op.create_index("ix_transactions_category", "transactions", ["user_id", "category_l1"])

    op.create_table(
        "beancount_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("transactions.id"),
                  unique=True, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("entry_date", sa.String(10), nullable=False),
        sa.Column("raw_beancount", sa.Text(), nullable=False),
        sa.Column("postings", sa.JSON(), default=[]),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "category_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("match_field", sa.String(20), default="merchant"),
        sa.Column("match_value", sa.String(255), nullable=False),
        sa.Column("category_l1", sa.String(50), nullable=False),
        sa.Column("category_l2", sa.String(50), nullable=True),
        sa.Column("priority", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "monthly_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("year_month", sa.String(7), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("ai_insight", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "year_month", name="uq_monthly_report"),
    )


def downgrade() -> None:
    op.drop_table("monthly_reports")
    op.drop_table("category_rules")
    op.drop_table("beancount_entries")
    op.drop_index("ix_transactions_category", "transactions")
    op.drop_index("ix_transactions_user_date", "transactions")
    op.drop_table("transactions")
    op.drop_table("bill_imports")
    op.drop_table("users")
