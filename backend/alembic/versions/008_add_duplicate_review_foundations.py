"""add duplicate review foundations

Revision ID: 008
Revises: 007
Create Date: 2026-03-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("bill_imports", "status", existing_type=sa.String(length=20), type_=sa.String(length=32), existing_nullable=False)

    op.add_column("transactions", sa.Column("duplicate_review_status", sa.String(length=20), nullable=False, server_default="not_needed"))
    op.add_column("transactions", sa.Column("duplicate_review_group_id", sa.String(length=36), nullable=True))

    op.create_table(
        "duplicate_review_groups",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("import_id", sa.String(length=36), sa.ForeignKey("bill_imports.id"), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("review_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("ai_suggestion", sa.String(length=20), nullable=True),
        sa.Column("ai_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("ai_reason", sa.Text(), nullable=True),
        sa.Column("candidate_date", sa.String(length=10), nullable=False),
        sa.Column("candidate_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("candidate_currency", sa.String(length=10), nullable=False, server_default="CNY"),
        sa.Column("transaction_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_duplicate_review_groups_import_id", "duplicate_review_groups", ["import_id"])
    op.create_index("ix_duplicate_review_groups_user_id", "duplicate_review_groups", ["user_id"])

    op.create_foreign_key(
        "fk_transactions_duplicate_review_group_id",
        "transactions",
        "duplicate_review_groups",
        ["duplicate_review_group_id"],
        ["id"],
    )

    op.create_index("ix_transactions_duplicate_review_group_id", "transactions", ["duplicate_review_group_id"])

    op.add_column("import_summaries", sa.Column("duplicate_review_group_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("import_summaries", sa.Column("duplicate_review_pair_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("import_summaries", sa.Column("duplicate_review_resolved_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("import_summaries", "duplicate_review_resolved_count")
    op.drop_column("import_summaries", "duplicate_review_pair_count")
    op.drop_column("import_summaries", "duplicate_review_group_count")

    op.drop_index("ix_transactions_duplicate_review_group_id", table_name="transactions")
    op.drop_constraint("fk_transactions_duplicate_review_group_id", "transactions", type_="foreignkey")

    op.drop_index("ix_duplicate_review_groups_user_id", table_name="duplicate_review_groups")
    op.drop_index("ix_duplicate_review_groups_import_id", table_name="duplicate_review_groups")
    op.drop_table("duplicate_review_groups")

    op.drop_column("transactions", "duplicate_review_group_id")
    op.drop_column("transactions", "duplicate_review_status")

    op.alter_column("bill_imports", "status", existing_type=sa.String(length=32), type_=sa.String(length=20), existing_nullable=False)
