"""add transaction cross-source dedupe key

Revision ID: 006
Revises: 005
Create Date: 2026-03-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("dedupe_key", sa.String(length=64), nullable=True))
    op.create_index("ix_transactions_dedupe_key", "transactions", ["dedupe_key"])

    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))

    op.execute(
        sa.text(
            """
            UPDATE transactions
            SET dedupe_key = encode(
                digest(
                    lower(coalesce(direction, '')) || '|' ||
                    to_char(abs(amount), 'FM999999999990.00') || '|' ||
                    upper(coalesce(nullif(trim(currency), ''), 'CNY')) || '|' ||
                    regexp_replace(lower(coalesce(merchant, '')), '\\s+', '', 'g') || '|' ||
                    regexp_replace(lower(coalesce(description, '')), '\\s+', '', 'g') || '|' ||
                    to_char(transaction_at, 'YYYY-MM-DD HH24:MI'),
                    'sha256'
                ),
                'hex'
            )
            WHERE dedupe_key IS NULL
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
                               PARTITION BY t.user_id, t.dedupe_key
                               ORDER BY t.created_at ASC, t.id ASC
                           ) AS rn
                    FROM transactions t
                    WHERE t.dedupe_key IS NOT NULL
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
                               PARTITION BY t.user_id, t.dedupe_key
                               ORDER BY t.created_at ASC, t.id ASC
                           ) AS rn
                    FROM transactions t
                    WHERE t.dedupe_key IS NOT NULL
                ) ranked
                WHERE ranked.rn > 1
            )
            """
        )
    )

    op.drop_constraint("uq_transaction_external_id", "transactions", type_="unique")
    op.create_unique_constraint(
        "uq_transaction_external_id",
        "transactions",
        ["user_id", "external_id"],
    )
    op.create_unique_constraint(
        "uq_transaction_dedupe_key",
        "transactions",
        ["user_id", "dedupe_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_transaction_dedupe_key", "transactions", type_="unique")
    op.drop_constraint("uq_transaction_external_id", "transactions", type_="unique")
    op.create_unique_constraint(
        "uq_transaction_external_id",
        "transactions",
        ["user_id", "source", "external_id"],
    )
    op.drop_index("ix_transactions_dedupe_key", table_name="transactions")
    op.drop_column("transactions", "dedupe_key")
