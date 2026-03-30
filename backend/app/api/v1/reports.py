from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application import report_service
from app.core.config import settings
from app.infrastructure.persistence.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/monthly/{year_month}")
def get_monthly_report(
    year_month: str,
    regenerate: bool = False,
    db: Session = Depends(get_db),
):
    """
    Get (or generate) monthly financial report.
    year_month format: YYYY-MM (e.g. 2025-03)
    """
    try:
        year, month = year_month.split("-")
        assert len(year) == 4 and 1 <= int(month) <= 12
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid year_month format. Use YYYY-MM")

    report = report_service.get_or_generate_report(
        db, settings.default_user_id, year_month, regenerate=regenerate
    )
    return report


@router.get("/months")
def list_months(db: Session = Depends(get_db)):
    """List all months that have transaction data."""
    months = report_service.list_available_months(db, settings.default_user_id)
    return {"months": months}


@router.get("/ranking/merchants")
def merchant_ranking(
    year_month: str | None = None,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Top merchants by spending amount."""
    from sqlalchemy import func, select
    from app.infrastructure.persistence.models.orm_models import TransactionORM
    from datetime import datetime

    q = (
        select(
            TransactionORM.merchant,
            func.sum(TransactionORM.amount).label("total"),
            func.count().label("cnt"),
        )
        .where(
            TransactionORM.user_id == settings.default_user_id,
            TransactionORM.direction == "expense",
            TransactionORM.merchant != "",
        )
        .group_by(TransactionORM.merchant)
        .order_by(func.sum(TransactionORM.amount).desc())
        .limit(limit)
    )

    if year_month:
        year, month = map(int, year_month.split("-"))
        start = datetime(year, month, 1)
        end = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
        q = q.where(
            TransactionORM.transaction_at >= start,
            TransactionORM.transaction_at < end,
        )

    rows = db.execute(q).all()
    return [
        {"merchant": r.merchant, "total": round(float(r.total), 2), "count": r.cnt}
        for r in rows
    ]


@router.get("/trends/categories/{year_month}")
def category_trends(
    year_month: str,
    months: int = 6,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    """Category expense trends for a rolling month window."""
    try:
        year, month = year_month.split("-")
        assert len(year) == 4 and 1 <= int(month) <= 12
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid year_month format. Use YYYY-MM")

    if months < 2 or months > 12:
        raise HTTPException(status_code=400, detail="months must be between 2 and 12")

    if limit < 1 or limit > 10:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 10")

    return report_service.get_category_trends(
        db,
        settings.default_user_id,
        year_month,
        months=months,
        limit=limit,
    )


@router.get("/beancount/{year_month}")
def export_beancount(year_month: str, db: Session = Depends(get_db)):
    """Export all transactions for a month as Beancount journal text."""
    from fastapi.responses import PlainTextResponse
    from sqlalchemy import select, and_
    from app.infrastructure.persistence.models.orm_models import BeancountEntryORM, TransactionORM
    from datetime import datetime

    year, month = map(int, year_month.split("-"))
    start = datetime(year, month, 1)
    end = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

    rows = db.scalars(
        select(BeancountEntryORM)
        .join(TransactionORM, BeancountEntryORM.transaction_id == TransactionORM.id)
        .where(
            BeancountEntryORM.user_id == settings.default_user_id,
            TransactionORM.transaction_at >= start,
            TransactionORM.transaction_at < end,
        )
        .order_by(BeancountEntryORM.entry_date)
    ).all()

    if not rows:
        raise HTTPException(status_code=404, detail="No data for this month")

    header = f'; Beancount Bot Export — {year_month}\noption "operating_currency" "CNY"\n\n'
    body = "\n\n".join(r.raw_beancount for r in rows)
    return PlainTextResponse(header + body, media_type="text/plain")
