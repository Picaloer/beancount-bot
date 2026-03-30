"""SQLAlchemy ORM models — separate from pure domain models."""
from datetime import datetime

from sqlalchemy import JSON, NUMERIC, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timezone import now_beijing
from app.infrastructure.persistence.database import Base


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)

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
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    llm_total_batches: Mapped[int] = mapped_column(Integer, default=0)
    llm_completed_batches: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    stage_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["UserORM"] = relationship(back_populates="imports")
    transactions: Mapped[list["TransactionORM"]] = relationship(back_populates="bill_import")
    stages: Mapped[list["ImportStageORM"]] = relationship(back_populates="bill_import")
    summary: Mapped["ImportSummaryORM | None"] = relationship(back_populates="bill_import", uselist=False)


class ImportStageORM(Base):
    __tablename__ = "import_stages"
    __table_args__ = (
        UniqueConstraint("import_id", "stage_key", name="uq_import_stage_import_stage_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    import_id: Mapped[str] = mapped_column(String(36), ForeignKey("bill_imports.id"), nullable=False, index=True)
    stage_key: Mapped[str] = mapped_column(String(50), nullable=False)
    stage_label: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)

    bill_import: Mapped["BillImportORM"] = relationship(back_populates="stages")


class ImportSummaryORM(Base):
    __tablename__ = "import_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    import_id: Mapped[str] = mapped_column(String(36), ForeignKey("bill_imports.id"), nullable=False, unique=True)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, default=0)
    beancount_entry_count: Mapped[int] = mapped_column(Integer, default=0)
    rule_based_count: Mapped[int] = mapped_column(Integer, default=0)
    llm_based_count: Mapped[int] = mapped_column(Integer, default=0)
    fallback_count: Mapped[int] = mapped_column(Integer, default=0)
    low_confidence_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing, onupdate=now_beijing)

    bill_import: Mapped["BillImportORM"] = relationship(back_populates="summary")


class RuntimeSettingORM(Base):
    __tablename__ = "runtime_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    llm_provider: Mapped[str] = mapped_column(String(20), default="claude")
    llm_model: Mapped[str] = mapped_column(String(100), default="claude-haiku-4-5-20251001")
    anthropic_api_key: Mapped[str] = mapped_column(Text, default="")
    deepseek_api_key: Mapped[str] = mapped_column(Text, default="")
    llm_base_url: Mapped[str] = mapped_column(String(255), default="")
    llm_batch_size: Mapped[int] = mapped_column(Integer, default=20)
    llm_max_concurrency: Mapped[int] = mapped_column(Integer, default=4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing, onupdate=now_beijing)


class TransactionORM(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "external_id", name="uq_transaction_external_id"),
        UniqueConstraint("user_id", "dedupe_key", name="uq_transaction_dedupe_key"),
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
    category_confidence: Mapped[float] = mapped_column(NUMERIC(4, 3), default=0)
    transaction_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)

    user: Mapped["UserORM"] = relationship(back_populates="category_rules")


class RuleSuggestionORM(Base):
    __tablename__ = "rule_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    match_field: Mapped[str] = mapped_column(String(20), nullable=False)
    match_value: Mapped[str] = mapped_column(String(255), nullable=False)
    category_l1: Mapped[str] = mapped_column(String(50), nullable=False)
    category_l2: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confidence: Mapped[float] = mapped_column(NUMERIC(4, 3), default=0)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    sample_transactions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["UserORM"] = relationship()


class MonthlyReportORM(Base):
    __tablename__ = "monthly_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)  # 2025-03
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    ai_insight: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_beijing)

    user: Mapped["UserORM"] = relationship(back_populates="budget_plans")
