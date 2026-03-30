"""add import runtime settings and progress metrics

Revision ID: 005
Revises: 004
Create Date: 2026-03-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("bill_imports", sa.Column("stage_message", sa.String(length=255), nullable=True))
    op.add_column("bill_imports", sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_imports", sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_imports", sa.Column("llm_total_batches", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_imports", sa.Column("llm_completed_batches", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_imports", sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_imports", sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("bill_imports", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("bill_imports", sa.Column("finished_at", sa.DateTime(), nullable=True))

    op.create_table(
        "runtime_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("llm_provider", sa.String(length=20), nullable=False, server_default="claude"),
        sa.Column("llm_model", sa.String(length=100), nullable=False, server_default="claude-haiku-4-5-20251001"),
        sa.Column("anthropic_api_key", sa.Text(), nullable=False, server_default=""),
        sa.Column("deepseek_api_key", sa.Text(), nullable=False, server_default=""),
        sa.Column("llm_base_url", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("llm_batch_size", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("llm_max_concurrency", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("runtime_settings")
    op.drop_column("bill_imports", "finished_at")
    op.drop_column("bill_imports", "started_at")
    op.drop_column("bill_imports", "output_tokens")
    op.drop_column("bill_imports", "input_tokens")
    op.drop_column("bill_imports", "llm_completed_batches")
    op.drop_column("bill_imports", "llm_total_batches")
    op.drop_column("bill_imports", "processed_rows")
    op.drop_column("bill_imports", "total_rows")
    op.drop_column("bill_imports", "stage_message")
