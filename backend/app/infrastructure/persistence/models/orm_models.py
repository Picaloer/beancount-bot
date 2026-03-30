"""SQLAlchemy ORM models — separate from pure domain models."""
from datetime import datetime

from sqlalchemy import JSON, NUMERIC, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    imports: Mapped[list["BillImportORM"]] = relationship(back_populates="user")
    transactions: Mapped[list["TransactionORM"]] = relationship(back_populates="user")
    category_rules: Mapped[list["CategoryRuleORM"]] = relationship(back_populates="user")
    budget_plans: Mapped[list["BudgetPlanORM"]] = relationship(back_populates="user")


class BillImportORM(Base):
    __tablename__ = "bill_imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # wechat / alipay
    file_name: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserORM"] = relationship(back_populates="imports")
    transactions: Mapped[list["TransactionORM"]] = relationship(back_populates="bill_import")


class TransactionORM(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "source", "external_id", name="uq_transaction_external_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    import_id: Mapped[str] = mapped_column(String(36), ForeignKey("bill_imports.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[float] = mapped_column(NUMERIC(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    merchant: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    category_l1: Mapped[str] = mapped_column(String(50), default="其他")
    category_l2: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category_source: Mapped[str] = mapped_column(String(20), default="fallback")
    transaction_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserORM"] = relationship(back_populates="transactions")
    bill_import: Mapped["BillImportORM"] = relationship(back_populates="transactions")
    beancount_entry: Mapped["BeancountEntryORM | None"] = relationship(
        back_populates="transaction", uselist=False
    )


class BeancountEntryORM(Base):
    __tablename__ = "beancount_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id"), unique=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    entry_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    raw_beancount: Mapped[str] = mapped_column(Text, nullable=False)
    postings: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transaction: Mapped["TransactionORM"] = relationship(back_populates="beancount_entry")


class CategoryRuleORM(Base):
    __tablename__ = "category_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    match_field: Mapped[str] = mapped_column(String(20), default="merchant")
    match_value: Mapped[str] = mapped_column(String(255), nullable=False)
    category_l1: Mapped[str] = mapped_column(String(50), nullable=False)
    category_l2: Mapped[str | None] = mapped_column(String(50), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserORM"] = relationship(back_populates="category_rules")


class MonthlyReportORM(Base):
    __tablename__ = "monthly_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)  # 2025-03
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    ai_insight: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BudgetPlanORM(Base):
    __tablename__ = "budget_plans"
    __table_args__ = (
        UniqueConstraint("user_id", "year_month", "category_l1", name="uq_budget_plan_user_month_category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)
    category_l1: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[float] = mapped_column(NUMERIC(12, 2), nullable=False)
    spent: Mapped[float] = mapped_column(NUMERIC(12, 2), nullable=False, default=0)
    usage_ratio: Mapped[float] = mapped_column(NUMERIC(8, 4), nullable=False, default=0)
    source: Mapped[str] = mapped_column(String(20), default="ai")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserORM"] = relationship(back_populates="budget_plans")
