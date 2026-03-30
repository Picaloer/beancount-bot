"""add transaction external id for dedupe

Revision ID: 002
Revises: 001
Create Date: 2026-03-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("external_id", sa.String(length=128), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE transactions
            SET external_id = COALESCE(
                raw_data->>'交易单号',
                raw_data->>'交易订单号',
                raw_data->>'交易号'
            )
            WHERE external_id IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            DELETE FROM beancount_entries
            WHERE transaction_id IN (
                SELECT id FROM (
                    SELECT t.id,
                           ROW_NUMBER() OVER (
                               PARTITION BY t.user_id, t.source, t.external_id
                               ORDER BY t.created_at ASC, t.id ASC
                           ) AS rn
                    FROM transactions t
                    WHERE t.external_id IS NOT NULL
                ) ranked
                WHERE ranked.rn > 1
            )
            """
        )
    )

    op.execute(
        sa.text(
            """
            DELETE FROM transactions
            WHERE id IN (
                SELECT id FROM (
                    SELECT t.id,
                           ROW_NUMBER() OVER (
                               PARTITION BY t.user_id, t.source, t.external_id
                               ORDER BY t.created_at ASC, t.id ASC
                           ) AS rn
                    FROM transactions t
                    WHERE t.external_id IS NOT NULL
                ) ranked
                WHERE ranked.rn > 1
            )
            """
        )
    )

    op.create_index("ix_transactions_external_id", "transactions", ["external_id"])
    op.create_unique_constraint(
        "uq_transaction_external_id",
        "transactions",
        ["user_id", "source", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_transaction_external_id", "transactions", type_="unique")
    op.drop_index("ix_transactions_external_id", table_name="transactions")
    op.drop_column("transactions", "external_id")
