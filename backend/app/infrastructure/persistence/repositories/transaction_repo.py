"""Transaction repository — thin SQLAlchemy wrapper over ORM."""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import and_, func, select, tuple_
from sqlalchemy.orm import Session

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
    db.refresh(imp)
    return imp


def update_import_status(
    db: Session, import_id: str, status: str, row_count: int = 0, error: str | None = None
) -> None:
    imp = db.get(BillImportORM, import_id)
    if imp:
        imp.status = status
        imp.row_count = row_count
        imp.error_message = error
        db.commit()


def bulk_create_transactions(
    db: Session,
    import_id: str,
    user_id: str,
    raw_transactions: list[RawTransaction],
) -> list[tuple[RawTransaction, str]]:
    existing_keys: set[tuple[str, str, str]] = set()
    external_ids = [raw.external_id for raw in raw_transactions if raw.external_id]
    if external_ids:
        existing_rows = db.scalars(
            select(TransactionORM).where(
                TransactionORM.user_id == user_id,
                TransactionORM.external_id.is_not(None),
                tuple_(TransactionORM.source, TransactionORM.external_id).in_(
                    [(raw.source.value, raw.external_id) for raw in raw_transactions if raw.external_id]
                ),
            )
        ).all()
        existing_keys = {
            (row.user_id, row.source, row.external_id)
            for row in existing_rows
            if row.external_id
        }

    inserted: list[tuple[RawTransaction, str]] = []
    for raw in raw_transactions:
        dedupe_key = (user_id, raw.source.value, raw.external_id) if raw.external_id else None
        if dedupe_key and dedupe_key in existing_keys:
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
            transaction_at=raw.transaction_at,
            external_id=raw.external_id,
            raw_data=raw.raw_data,
        )
        db.add(orm)
        inserted.append((raw, tx_id))
        if dedupe_key:
            existing_keys.add(dedupe_key)
    db.commit()
    return inserted


def update_transaction_category(
    db: Session,
    transaction_id: str,
    category_l1: str,
    category_l2: str | None,
    source: str,
) -> None:
    tx = db.get(TransactionORM, transaction_id)
    if tx:
        tx.category_l1 = category_l1
        tx.category_l2 = category_l2
        tx.category_source = source
    db.commit()


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
    Returns {'deleted_transactions': N, 'affected_months': [...]}
    Raises ValueError if import not found or belongs to another user.
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

    affected_months: set[str] = set()
    tx_ids = [tx.id for tx in txs]
    for tx in txs:
        affected_months.add(tx.transaction_at.strftime("%Y-%m"))

    if tx_ids:
        entries = db.scalars(
            select(BeancountEntryORM).where(BeancountEntryORM.transaction_id.in_(tx_ids))
        ).all()
        for entry in entries:
            db.delete(entry)

    for tx in txs:
        db.delete(tx)

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
