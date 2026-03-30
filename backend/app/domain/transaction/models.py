"""
Pure domain models (no ORM dependency).
These are the canonical objects passed between layers.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TransactionDirection(str, Enum):
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"


class BillSource(str, Enum):
    WECHAT = "wechat"
    ALIPAY = "alipay"


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
    # Platform-issued order number used for deduplication across re-imports
    external_id: str | None = None


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
    created_at: datetime = field(default_factory=datetime.utcnow)
