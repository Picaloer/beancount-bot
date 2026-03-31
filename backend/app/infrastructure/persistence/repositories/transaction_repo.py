"""Transaction repository — thin SQLAlchemy wrapper over ORM."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.timezone import ensure_beijing_naive, isoformat_beijing, now_beijing
from app.domain.transaction.models import (
    BillSource,
    CategorySource,
    RawTransaction,
    Transaction,
    TransactionDirection,
)
from app.infrastructure.persistence.models.orm_models import (
    BeancountEntryORM,
    BillImportORM,
    BudgetPlanORM,
    CategoryRuleORM,
    ImportStageORM,
    ImportSummaryORM,
    RuleSuggestionORM,
    RuntimeSettingORM,
    TransactionORM,
    UserORM,
)


def ensure_user(db: Session, user_id: str) -> UserORM:
    user = db.get(UserORM, user_id)
    if not user:
        user = UserORM(id=user_id, email=f"{user_id}@local")
        db.add(user)
        db.commit()
    return user


def create_import(db: Session, user_id: str, source: str, file_name: str) -> BillImportORM:
    ensure_user(db, user_id)
    imp = BillImportORM(
        id=str(uuid4()),
        user_id=user_id,
        source=source,
        file_name=file_name,
        status="pending",
    )
    db.add(imp)
    db.commit()

    _initialize_import_stages(db, imp.id)
    _upsert_import_summary(db, imp.id)

    db.refresh(imp)
    return imp


def update_import_status(
    db: Session,
    import_id: str,
    status: str | None = None,
    row_count: int | None = None,
    total_rows: int | None = None,
    processed_rows: int | None = None,
    llm_total_batches: int | None = None,
    llm_completed_batches: int | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    stage_message: str | None = None,
    error: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> None:
    imp = db.get(BillImportORM, import_id)
    if not imp:
        return

    if status is not None:
        imp.status = status
    if row_count is not None:
        imp.row_count = row_count
    if total_rows is not None:
        imp.total_rows = total_rows
    if processed_rows is not None:
        imp.processed_rows = processed_rows
    if llm_total_batches is not None:
        imp.llm_total_batches = llm_total_batches
    if llm_completed_batches is not None:
        imp.llm_completed_batches = llm_completed_batches
    if input_tokens is not None:
        imp.input_tokens = input_tokens
    if output_tokens is not None:
        imp.output_tokens = output_tokens
    if stage_message is not None:
        imp.stage_message = stage_message
    if error is not None:
        imp.error_message = error
    if started_at is not None:
        imp.started_at = ensure_beijing_naive(started_at)
    if finished_at is not None:
        imp.finished_at = ensure_beijing_naive(finished_at)
    db.commit()


def _initialize_import_stages(db: Session, import_id: str) -> None:
    stage_definitions = [
        ("parse", "解析账单"),
        ("dedupe", "识别重复交易"),
        ("classify", "分类交易"),
        ("beancount", "生成 Beancount 分录"),
    ]
    for stage_key, stage_label in stage_definitions:
        db.add(
            ImportStageORM(
                id=str(uuid4()),
                import_id=import_id,
                stage_key=stage_key,
                stage_label=stage_label,
                status="pending",
            )
        )
    db.commit()


def update_import_stage(
    db: Session,
    import_id: str,
    stage_key: str,
    *,
    status: str,
    message: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> None:
    stage = db.scalar(
        select(ImportStageORM).where(
            ImportStageORM.import_id == import_id,
            ImportStageORM.stage_key == stage_key,
        )
    )
    if not stage:
        return

    stage.status = status
    if message is not None:
        stage.message = message
    if started_at is not None:
        stage.started_at = ensure_beijing_naive(started_at)
    if finished_at is not None:
        stage.finished_at = ensure_beijing_naive(finished_at)
    db.commit()


def _upsert_import_summary(
    db: Session,
    import_id: str,
    *,
    inserted_count: int | None = None,
    duplicate_count: int | None = None,
    beancount_entry_count: int | None = None,
    rule_based_count: int | None = None,
    llm_based_count: int | None = None,
    fallback_count: int | None = None,
    low_confidence_count: int | None = None,
) -> ImportSummaryORM:
    summary = db.scalar(select(ImportSummaryORM).where(ImportSummaryORM.import_id == import_id))
    if summary is None:
        summary = ImportSummaryORM(id=str(uuid4()), import_id=import_id)
        db.add(summary)

    if inserted_count is not None:
        summary.inserted_count = inserted_count
    if duplicate_count is not None:
        summary.duplicate_count = duplicate_count
    if beancount_entry_count is not None:
        summary.beancount_entry_count = beancount_entry_count
    if rule_based_count is not None:
        summary.rule_based_count = rule_based_count
    if llm_based_count is not None:
        summary.llm_based_count = llm_based_count
    if fallback_count is not None:
        summary.fallback_count = fallback_count
    if low_confidence_count is not None:
        summary.low_confidence_count = low_confidence_count

    db.commit()
    db.refresh(summary)
    return summary


def update_import_summary(
    db: Session,
    import_id: str,
    *,
    inserted_count: int | None = None,
    duplicate_count: int | None = None,
    beancount_entry_count: int | None = None,
    rule_based_count: int | None = None,
    llm_based_count: int | None = None,
    fallback_count: int | None = None,
    low_confidence_count: int | None = None,
) -> None:
    _upsert_import_summary(
        db,
        import_id,
        inserted_count=inserted_count,
        duplicate_count=duplicate_count,
        beancount_entry_count=beancount_entry_count,
        rule_based_count=rule_based_count,
        llm_based_count=llm_based_count,
        fallback_count=fallback_count,
        low_confidence_count=low_confidence_count,
    )


def get_import_detail(db: Session, import_id: str, user_id: str) -> dict | None:
    imp = db.scalar(
        select(BillImportORM).where(
            BillImportORM.id == import_id,
            BillImportORM.user_id == user_id,
        )
    )
    if not imp:
        return None

    stages = db.scalars(
        select(ImportStageORM)
        .where(ImportStageORM.import_id == import_id)
        .order_by(ImportStageORM.created_at.asc())
    ).all()
    summary = db.scalar(select(ImportSummaryORM).where(ImportSummaryORM.import_id == import_id))

    return {
        "import_id": imp.id,
        "source": imp.source,
        "file_name": imp.file_name,
        "status": imp.status,
        "row_count": imp.row_count,
        "total_rows": imp.total_rows,
        "processed_rows": imp.processed_rows,
        "llm_total_batches": imp.llm_total_batches,
        "llm_completed_batches": imp.llm_completed_batches,
        "input_tokens": imp.input_tokens,
        "output_tokens": imp.output_tokens,
        "total_tokens": imp.input_tokens + imp.output_tokens,
        "stage_message": imp.stage_message,
        "error_message": imp.error_message,
        "imported_at": isoformat_beijing(imp.imported_at),
        "started_at": isoformat_beijing(imp.started_at) if imp.started_at else None,
        "finished_at": isoformat_beijing(imp.finished_at) if imp.finished_at else None,
        "stages": [
            {
                "stage_key": stage.stage_key,
                "stage_label": stage.stage_label,
                "status": stage.status,
                "message": stage.message,
                "started_at": isoformat_beijing(stage.started_at) if stage.started_at else None,
                "finished_at": isoformat_beijing(stage.finished_at) if stage.finished_at else None,
            }
            for stage in stages
        ],
        "summary": {
            "inserted_count": summary.inserted_count if summary else 0,
            "duplicate_count": summary.duplicate_count if summary else 0,
            "beancount_entry_count": summary.beancount_entry_count if summary else 0,
            "rule_based_count": summary.rule_based_count if summary else 0,
            "llm_based_count": summary.llm_based_count if summary else 0,
            "fallback_count": summary.fallback_count if summary else 0,
            "low_confidence_count": summary.low_confidence_count if summary else 0,
        },
    }


def increment_import_usage(
    db: Session,
    import_id: str,
    *,
    processed_rows: int = 0,
    llm_completed_batches: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    imp = db.get(BillImportORM, import_id)
    if not imp:
        return
    imp.processed_rows += processed_rows
    imp.llm_completed_batches += llm_completed_batches
    imp.input_tokens += input_tokens
    imp.output_tokens += output_tokens
    db.commit()


def get_runtime_settings(db: Session, user_id: str) -> RuntimeSettingORM | None:
    return db.scalar(select(RuntimeSettingORM).where(RuntimeSettingORM.user_id == user_id))


def bulk_create_transactions(
    db: Session,
    import_id: str,
    user_id: str,
    raw_transactions: list[RawTransaction],
) -> list[tuple[RawTransaction, str]]:
    existing_external_ids = {
        row[0]
        for row in db.execute(
            select(TransactionORM.external_id).where(
                TransactionORM.user_id == user_id,
                TransactionORM.external_id.is_not(None),
                TransactionORM.external_id.in_([raw.external_id for raw in raw_transactions if raw.external_id]),
            )
        ).all()
        if row[0]
    }
    existing_dedupe_keys = {
        row[0]
        for row in db.execute(
            select(TransactionORM.dedupe_key).where(
                TransactionORM.user_id == user_id,
                TransactionORM.dedupe_key.is_not(None),
                TransactionORM.dedupe_key.in_([raw.dedupe_key for raw in raw_transactions if raw.dedupe_key]),
            )
        ).all()
        if row[0]
    }

    inserted: list[tuple[RawTransaction, str]] = []
    for raw in raw_transactions:
        if raw.external_id and raw.external_id in existing_external_ids:
            continue
        if raw.dedupe_key and raw.dedupe_key in existing_dedupe_keys:
            continue

        tx_id = str(uuid4())
        orm = TransactionORM(
            id=tx_id,
            user_id=user_id,
            import_id=import_id,
            source=raw.source.value,
            direction=raw.direction.value,
            amount=float(raw.amount),
            currency=raw.currency,
            merchant=raw.merchant,
            description=raw.description,
            transaction_at=ensure_beijing_naive(raw.transaction_at),
            external_id=raw.external_id,
            dedupe_key=raw.dedupe_key,
            raw_data=raw.raw_data,
        )
        db.add(orm)
        inserted.append((raw, tx_id))
        if raw.external_id:
            existing_external_ids.add(raw.external_id)
        if raw.dedupe_key:
            existing_dedupe_keys.add(raw.dedupe_key)
    db.commit()
    return inserted


def update_transaction_category(
    db: Session,
    transaction_id: str,
    category_l1: str,
    category_l2: str | None,
    source: str,
    confidence: float | None = None,
) -> None:
    tx = db.get(TransactionORM, transaction_id)
    if tx:
        tx.category_l1 = category_l1
        tx.category_l2 = category_l2
        tx.category_source = source
        if confidence is not None:
            tx.category_confidence = confidence
    db.commit()


def save_rule_suggestion(
    db: Session,
    user_id: str,
    match_field: str,
    match_value: str,
    category_l1: str,
    category_l2: str | None,
    confidence: float,
    source: str,
    reason: str | None = None,
    evidence_count: int = 1,
    sample_transactions: list | None = None,
) -> RuleSuggestionORM:
    ensure_user(db, user_id)

    normalized_match_value = match_value.strip()
    if not normalized_match_value:
        raise ValueError("match_value cannot be empty")

    existing_pending = db.scalar(
        select(RuleSuggestionORM).where(
            RuleSuggestionORM.user_id == user_id,
            RuleSuggestionORM.match_field == match_field,
            RuleSuggestionORM.match_value == normalized_match_value,
            RuleSuggestionORM.category_l1 == category_l1,
            RuleSuggestionORM.category_l2 == category_l2,
            RuleSuggestionORM.status == "pending",
        )
    )
    if existing_pending:
        existing_pending.confidence = max(float(existing_pending.confidence), confidence)
        existing_pending.evidence_count = max(existing_pending.evidence_count, evidence_count)
        existing_pending.source = source
        existing_pending.reason = reason
        if sample_transactions is not None:
            existing_pending.sample_transactions = sample_transactions
        db.commit()
        db.refresh(existing_pending)
        return existing_pending

    suggestion = RuleSuggestionORM(
        id=str(uuid4()),
        user_id=user_id,
        match_field=match_field,
        match_value=normalized_match_value,
        category_l1=category_l1,
        category_l2=category_l2,
        confidence=confidence,
        source=source,
        status="pending",
        reason=reason,
        evidence_count=evidence_count,
        sample_transactions=sample_transactions or [],
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def list_rule_suggestions(db: Session, user_id: str, status: str = "pending") -> list[RuleSuggestionORM]:
    return db.scalars(
        select(RuleSuggestionORM)
        .where(
            RuleSuggestionORM.user_id == user_id,
            RuleSuggestionORM.status == status,
        )
        .order_by(RuleSuggestionORM.created_at.desc())
    ).all()


def generate_rule_suggestions_from_history(
    db: Session,
    user_id: str,
    min_llm_confidence: float = 0.85,
    min_llm_evidence: int = 2,
) -> list[RuleSuggestionORM]:
    rows = db.scalars(
        select(TransactionORM).where(
            TransactionORM.user_id == user_id,
            TransactionORM.merchant != "",
            TransactionORM.category_l1 != "其他",
            TransactionORM.category_source.in_([CategorySource.LLM.value, CategorySource.MANUAL.value]),
        )
    ).all()

    grouped: dict[tuple[str, str, str | None], list[TransactionORM]] = {}
    for row in rows:
        key = (row.merchant.strip(), row.category_l1, row.category_l2)
        if not key[0]:
            continue
        grouped.setdefault(key, []).append(row)

    created: list[RuleSuggestionORM] = []
    for (merchant, category_l1, category_l2), txs in grouped.items():
        manual_txs = [tx for tx in txs if tx.category_source == CategorySource.MANUAL.value]
        llm_txs = [
            tx
            for tx in txs
            if tx.category_source == CategorySource.LLM.value
            and float(tx.category_confidence) >= min_llm_confidence
        ]

        if manual_txs:
            candidate_txs = manual_txs
            source = "manual_feedback"
            confidence = 1.0
            reason = "历史上用户手动修正过该商户的分类，建议确认后沉淀为规则。"
        elif len(llm_txs) >= min_llm_evidence:
            candidate_txs = llm_txs
            source = "llm_feedback"
            confidence = round(
                sum(float(tx.category_confidence) for tx in llm_txs) / len(llm_txs),
                3,
            )
            reason = "该商户被大模型多次高置信度分类到同一类别，建议人工确认后转为规则。"
        else:
            continue

        existing_rule = db.scalar(
            select(CategoryRuleORM).where(
                CategoryRuleORM.user_id == user_id,
                CategoryRuleORM.match_field == "merchant",
                CategoryRuleORM.match_value == merchant,
                CategoryRuleORM.category_l1 == category_l1,
                CategoryRuleORM.category_l2 == category_l2,
            )
        )
        if existing_rule:
            continue

        sample_transactions = [
            {
                "transaction_id": tx.id,
                "merchant": tx.merchant,
                "description": tx.description,
                "amount": float(tx.amount),
                "source": tx.source,
                "transaction_at": isoformat_beijing(tx.transaction_at),
                "category_source": tx.category_source,
                "category_confidence": float(tx.category_confidence),
            }
            for tx in candidate_txs[:5]
        ]
        created.append(
            save_rule_suggestion(
                db,
                user_id=user_id,
                match_field="merchant",
                match_value=merchant,
                category_l1=category_l1,
                category_l2=category_l2,
                confidence=confidence,
                source=source,
                reason=reason,
                evidence_count=len(candidate_txs),
                sample_transactions=sample_transactions,
            )
        )

    return created


def approve_rule_suggestion(db: Session, suggestion_id: str, user_id: str) -> CategoryRuleORM:
    suggestion = db.get(RuleSuggestionORM, suggestion_id)
    if not suggestion or suggestion.user_id != user_id:
        raise ValueError("Rule suggestion not found")
    if suggestion.status != "pending":
        raise ValueError("Rule suggestion is not pending")

    existing_rule = db.scalar(
        select(CategoryRuleORM).where(
            CategoryRuleORM.user_id == user_id,
            CategoryRuleORM.match_field == suggestion.match_field,
            CategoryRuleORM.match_value == suggestion.match_value,
            CategoryRuleORM.category_l1 == suggestion.category_l1,
            CategoryRuleORM.category_l2 == suggestion.category_l2,
        )
    )
    if existing_rule is None:
        existing_rule = CategoryRuleORM(
            id=str(uuid4()),
            user_id=user_id,
            match_field=suggestion.match_field,
            match_value=suggestion.match_value,
            category_l1=suggestion.category_l1,
            category_l2=suggestion.category_l2,
            priority=10,
        )
        db.add(existing_rule)

    suggestion.status = "approved"
    suggestion.resolved_at = now_beijing()
    db.commit()
    db.refresh(existing_rule)
    return existing_rule


def reject_rule_suggestion(db: Session, suggestion_id: str, user_id: str) -> RuleSuggestionORM:
    suggestion = db.get(RuleSuggestionORM, suggestion_id)
    if not suggestion or suggestion.user_id != user_id:
        raise ValueError("Rule suggestion not found")
    if suggestion.status != "pending":
        raise ValueError("Rule suggestion is not pending")

    suggestion.status = "rejected"
    suggestion.resolved_at = now_beijing()
    db.commit()
    db.refresh(suggestion)
    return suggestion


def save_beancount_entry(
    db: Session, transaction_id: str, user_id: str, entry_date: str, raw_beancount: str, postings: list
) -> None:
    existing = db.scalar(
        select(BeancountEntryORM).where(BeancountEntryORM.transaction_id == transaction_id)
    )
    if existing:
        existing.raw_beancount = raw_beancount
        existing.postings = postings
    else:
        db.add(BeancountEntryORM(
            id=str(uuid4()),
            transaction_id=transaction_id,
            user_id=user_id,
            entry_date=entry_date,
            raw_beancount=raw_beancount,
            postings=postings,
        ))
    db.commit()


def delete_import(db: Session, import_id: str, user_id: str) -> dict:
    """
    Cascade-delete an import and all associated data.
    Returns {'deleted_transactions': N, 'affected_months': [...]}.
    """
    from app.infrastructure.persistence.models.orm_models import MonthlyReportORM

    imp = db.scalar(
        select(BillImportORM).where(
            BillImportORM.id == import_id,
            BillImportORM.user_id == user_id,
        )
    )
    if not imp:
        raise ValueError(f"Import {import_id} not found")

    if imp.status in ("processing", "classifying"):
        raise ValueError("Cannot delete an import that is currently being processed")

    txs = db.scalars(
        select(TransactionORM).where(
            TransactionORM.import_id == import_id,
            TransactionORM.user_id == user_id,
        )
    ).all()

    affected_months: set[str] = {tx.transaction_at.strftime("%Y-%m") for tx in txs}
    tx_ids = [tx.id for tx in txs]

    if tx_ids:
        entries = db.scalars(
            select(BeancountEntryORM).where(BeancountEntryORM.transaction_id.in_(tx_ids))
        ).all()
        for entry in entries:
            db.delete(entry)

    groups = db.scalars(
        select(DuplicateReviewGroupORM).where(
            DuplicateReviewGroupORM.import_id == import_id,
            DuplicateReviewGroupORM.user_id == user_id,
        )
    ).all()

    for tx in txs:
        tx.duplicate_review_group_id = None
        db.delete(tx)

    for group in groups:
        db.delete(group)

    summary = db.scalar(select(ImportSummaryORM).where(ImportSummaryORM.import_id == import_id))
    if summary:
        db.delete(summary)

    stages = db.scalars(select(ImportStageORM).where(ImportStageORM.import_id == import_id)).all()
    for stage in stages:
        db.delete(stage)

    for ym in affected_months:
        cached_report = db.scalar(
            select(MonthlyReportORM).where(
                MonthlyReportORM.user_id == user_id,
                MonthlyReportORM.year_month == ym,
            )
        )
        if cached_report:
            db.delete(cached_report)

        budget_rows = db.scalars(
            select(BudgetPlanORM).where(
                BudgetPlanORM.user_id == user_id,
                BudgetPlanORM.year_month == ym,
            )
        ).all()
        for budget in budget_rows:
            db.delete(budget)

    db.delete(imp)
    db.commit()

    return {
        "deleted_transactions": len(tx_ids),
        "affected_months": sorted(affected_months),
    }



def get_transactions(
    db: Session,
    user_id: str,
    year_month: str | None = None,
    category_l1: str | None = None,
    direction: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[TransactionORM], int]:
    q = select(TransactionORM).where(TransactionORM.user_id == user_id)

    if year_month:
        year, month = map(int, year_month.split("-"))
        start = datetime(year, month, 1)
        end = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
        q = q.where(and_(TransactionORM.transaction_at >= start, TransactionORM.transaction_at < end))

    if category_l1:
        q = q.where(TransactionORM.category_l1 == category_l1)

    if direction:
        q = q.where(TransactionORM.direction == direction)

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(
        q.order_by(TransactionORM.transaction_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total or 0


def get_monthly_stats(db: Session, user_id: str, year_month: str) -> dict:
    year, month = map(int, year_month.split("-"))
    start = datetime(year, month, 1)
    end = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

    rows = db.scalars(
        select(TransactionORM).where(
            and_(
                TransactionORM.user_id == user_id,
                TransactionORM.transaction_at >= start,
                TransactionORM.transaction_at < end,
            )
        )
    ).all()

    total_expense = sum(float(r.amount) for r in rows if r.direction == "expense")
    total_income = sum(float(r.amount) for r in rows if r.direction == "income")

    cat_totals: dict[str, float] = {}
    for r in rows:
        if r.direction == "expense":
            cat_totals[r.category_l1] = cat_totals.get(r.category_l1, 0) + float(r.amount)

    category_breakdown = [
        {
            "category_l1": cat,
            "amount": round(amt, 2),
            "percentage": round(amt / total_expense * 100, 1) if total_expense else 0,
        }
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    merchant_totals: dict[str, dict] = {}
    for r in rows:
        if r.direction == "expense" and r.merchant:
            if r.merchant not in merchant_totals:
                merchant_totals[r.merchant] = {"merchant": r.merchant, "amount": 0.0, "count": 0}
            merchant_totals[r.merchant]["amount"] += float(r.amount)
            merchant_totals[r.merchant]["count"] += 1
    top_merchants = sorted(merchant_totals.values(), key=lambda x: x["amount"], reverse=True)[:10]
    for m in top_merchants:
        m["amount"] = round(m["amount"], 2)

    weekly: dict[int, float] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in rows:
        if r.direction == "expense":
            week = min((r.transaction_at.day - 1) // 7 + 1, 5)
            weekly[week] = weekly.get(week, 0) + float(r.amount)

    return {
        "year_month": year_month,
        "total_expense": round(total_expense, 2),
        "total_income": round(total_income, 2),
        "net": round(total_income - total_expense, 2),
        "transaction_count": len(rows),
        "category_breakdown": category_breakdown,
        "top_merchants": top_merchants,
        "weekly_expense": [{"week": k, "amount": round(v, 2)} for k, v in sorted(weekly.items())],
    }


def get_category_trends(
    db: Session,
    user_id: str,
    year_month: str,
    months: int = 6,
    limit: int = 5,
) -> dict:
    month_labels = _build_month_window(year_month, months)
    start_year, start_month = map(int, month_labels[0].split("-"))
    end_year, end_month = map(int, year_month.split("-"))
    start = datetime(start_year, start_month, 1)
    end = datetime(end_year + 1, 1, 1) if end_month == 12 else datetime(end_year, end_month + 1, 1)

    rows = db.scalars(
        select(TransactionORM).where(
            and_(
                TransactionORM.user_id == user_id,
                TransactionORM.direction == "expense",
                TransactionORM.transaction_at >= start,
                TransactionORM.transaction_at < end,
            )
        )
    ).all()

    category_totals: dict[str, float] = {}
    monthly_totals: dict[str, dict[str, float]] = {label: {} for label in month_labels}

    for row in rows:
        label = row.transaction_at.strftime("%Y-%m")
        category = row.category_l1 or "其他"
        amount = float(row.amount)
        category_totals[category] = category_totals.get(category, 0.0) + amount

        month_bucket = monthly_totals.setdefault(label, {})
        month_bucket[category] = month_bucket.get(category, 0.0) + amount

    top_categories = [
        category
        for category, _ in sorted(
            category_totals.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:limit]
    ]

    points: list[dict[str, str | float]] = []
    for label in month_labels:
        point: dict[str, str | float] = {"year_month": label}
        for category in top_categories:
            point[category] = round(monthly_totals.get(label, {}).get(category, 0.0), 2)
        points.append(point)

    return {
        "year_month": year_month,
        "months": month_labels,
        "categories": top_categories,
        "points": points,
        "top_categories": [
            {
                "category_l1": category,
                "total": round(category_totals[category], 2),
            }
            for category in top_categories
        ],
    }


def get_budget_plan(db: Session, user_id: str, year_month: str) -> list[BudgetPlanORM]:
    return db.scalars(
        select(BudgetPlanORM)
        .where(
            BudgetPlanORM.user_id == user_id,
            BudgetPlanORM.year_month == year_month,
        )
        .order_by(BudgetPlanORM.amount.desc(), BudgetPlanORM.category_l1.asc())
    ).all()


def replace_budget_plan(
    db: Session,
    user_id: str,
    year_month: str,
    items: list[dict[str, float | str]],
) -> list[BudgetPlanORM]:
    ensure_user(db, user_id)

    existing = db.scalars(
        select(BudgetPlanORM).where(
            BudgetPlanORM.user_id == user_id,
            BudgetPlanORM.year_month == year_month,
        )
    ).all()
    for row in existing:
        db.delete(row)
    db.flush()

    created: list[BudgetPlanORM] = []
    for item in items:
        orm = BudgetPlanORM(
            id=str(uuid4()),
            user_id=user_id,
            year_month=year_month,
            category_l1=str(item["category_l1"]),
            amount=float(item["amount"]),
            spent=float(item["spent"]),
            usage_ratio=float(item["usage_ratio"]),
            source=str(item.get("source", "ai")),
        )
        db.add(orm)
        created.append(orm)

    db.commit()
    for row in created:
        db.refresh(row)
    return created


def _build_month_window(year_month: str, months: int) -> list[str]:
    year, month = map(int, year_month.split("-"))
    labels: list[str] = []

    for offset in range(months - 1, -1, -1):
        current_year = year
        current_month = month - offset
        while current_month <= 0:
            current_year -= 1
            current_month += 12
        labels.append(f"{current_year:04d}-{current_month:02d}")

    return labels
