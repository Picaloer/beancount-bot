"""
Pure domain models (no ORM dependency).
These are the canonical objects passed between layers.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import sha256
from typing import Any

from app.core.timezone import now_beijing


class TransactionDirection(str, Enum):
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


class BillSource(str, Enum):
    WECHAT = "wechat"
    ALIPAY = "alipay"
    CMB = "cmb"


class CategorySource(str, Enum):
    USER_RULE = "user_rule"
    SYSTEM_RULE = "system_rule"
    LLM = "llm"
    MANUAL = "manual"
    FALLBACK = "fallback"


@dataclass
class RawTransaction:
    """Output of parser — unclassified, un-enriched."""
    source: BillSource
    direction: TransactionDirection
    amount: float
    currency: str
    merchant: str
    description: str
    transaction_at: datetime
    raw_data: dict[str, Any] = field(default_factory=dict)
    # Platform-issued order number used for exact same-order deduplication.
    external_id: str | None = None
    # Cross-source fingerprint used to suppress the same underlying payment
    # appearing in bank statements and wallet exports.
    dedupe_key: str | None = None


@dataclass
class Transaction:
    """Fully enriched domain transaction."""
    id: str
    user_id: str
    import_id: str
    source: BillSource
    direction: TransactionDirection
    amount: float
    currency: str
    merchant: str
    description: str
    transaction_at: datetime
    category_l1: str = "其他"
    category_l2: str | None = None
    category_source: CategorySource = CategorySource.FALLBACK
    raw_data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=now_beijing)


def build_transaction_dedupe_key(
    *,
    direction: TransactionDirection,
    amount: float,
    currency: str,
    merchant: str,
    description: str,
    transaction_at: datetime,
) -> str:
    normalized_amount = f"{abs(float(amount)):.2f}"
    normalized_currency = (currency or "CNY").strip().upper() or "CNY"
    normalized_merchant = _normalize_dedupe_text(merchant)
    normalized_description = _normalize_dedupe_text(description)
    timestamp = transaction_at.strftime("%Y-%m-%d %H:%M")
    raw = "|".join(
        [
            direction.value,
            normalized_amount,
            normalized_currency,
            normalized_merchant,
            normalized_description,
            timestamp,
        ]
    )
    return sha256(raw.encode("utf-8")).hexdigest()


def _normalize_dedupe_text(value: str) -> str:
    return "".join(value.lower().split())
