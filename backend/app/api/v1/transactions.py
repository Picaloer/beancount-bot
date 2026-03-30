from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from app.core.config import settings
from app.domain.classification.category_tree import get_l2_options, is_valid_l1
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories import transaction_repo as repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


class CategoryUpdate(BaseModel):
    category_l1: str
    category_l2: str | None = None


@router.get("")
def list_transactions(
    year_month: str | None = None,
    category_l1: str | None = None,
    direction: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    """List transactions with optional filters."""
    rows, total = repo.get_transactions(
        db,
        user_id=settings.default_user_id,
        year_month=year_month,
        category_l1=category_l1,
        direction=direction,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_serialize(r) for r in rows],
    }


@router.patch("/{transaction_id}/category")
def update_category(
    transaction_id: str,
    body: CategoryUpdate,
    db: Session = Depends(get_db),
):
    """Manually override transaction category."""
    from sqlalchemy import select

    from app.domain.beancount.engine import BeancountEngine
    from app.domain.transaction.models import (
        BillSource,
        CategorySource,
        Transaction,
        TransactionDirection,
    )
    from app.infrastructure.persistence.models.orm_models import MonthlyReportORM, TransactionORM

    tx = db.get(TransactionORM, transaction_id)
    if not tx or tx.user_id != settings.default_user_id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if not is_valid_l1(body.category_l1):
        raise HTTPException(status_code=400, detail="Invalid category_l1")
    if body.category_l2 and body.category_l2 not in get_l2_options(body.category_l1):
        raise HTTPException(status_code=400, detail="Invalid category_l2 for category_l1")

    repo.update_transaction_category(
        db,
        transaction_id,
        body.category_l1,
        body.category_l2,
        "manual",
        confidence=1.0,
    )

    if tx.merchant.strip():
        repo.save_rule_suggestion(
            db,
            user_id=tx.user_id,
            match_field="merchant",
            match_value=tx.merchant,
            category_l1=body.category_l1,
            category_l2=body.category_l2,
            confidence=1.0,
            source="manual_feedback",
            reason="用户手动修正了该商户的分类，建议确认后沉淀为规则。",
            evidence_count=1,
            sample_transactions=[
                {
                    "transaction_id": tx.id,
                    "merchant": tx.merchant,
                    "description": tx.description,
                    "amount": float(tx.amount),
                    "source": tx.source,
                    "transaction_at": tx.transaction_at.isoformat(),
                }
            ],
        )

    try:
        refreshed_tx = db.get(TransactionORM, transaction_id)
        if refreshed_tx:
            cached_report = db.scalar(
                select(MonthlyReportORM).where(
                    MonthlyReportORM.user_id == refreshed_tx.user_id,
                    MonthlyReportORM.year_month == refreshed_tx.transaction_at.strftime("%Y-%m"),
                )
            )
            if cached_report:
                db.delete(cached_report)
                db.commit()

            engine = BeancountEngine()
            entry = engine.generate_entry(
                Transaction(
                    id=refreshed_tx.id,
                    user_id=refreshed_tx.user_id,
                    import_id=refreshed_tx.import_id,
                    source=BillSource(refreshed_tx.source),
                    direction=TransactionDirection(refreshed_tx.direction),
                    amount=float(refreshed_tx.amount),
                    currency=refreshed_tx.currency,
                    merchant=refreshed_tx.merchant,
                    description=refreshed_tx.description,
                    transaction_at=refreshed_tx.transaction_at,
                    category_l1=refreshed_tx.category_l1,
                    category_l2=refreshed_tx.category_l2,
                    category_source=CategorySource.MANUAL,
                    raw_data=refreshed_tx.raw_data,
                )
            )
            postings = [
                {"account": posting.account, "amount": str(posting.amount), "currency": posting.currency}
                for posting in entry.postings
            ]
            repo.save_beancount_entry(
                db,
                refreshed_tx.id,
                refreshed_tx.user_id,
                entry.date,
                entry.render(),
                postings,
            )
    except Exception as exc:
        logger.warning("Failed to refresh Beancount entry for %s: %s", transaction_id, exc)

    return {"ok": True}


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Quick stats: total expense/income across all time."""
    from sqlalchemy import func, select
    from app.infrastructure.persistence.models.orm_models import TransactionORM

    rows = db.execute(
        select(
            TransactionORM.direction,
            func.sum(TransactionORM.amount).label("total"),
            func.count().label("cnt"),
        )
        .where(TransactionORM.user_id == settings.default_user_id)
        .group_by(TransactionORM.direction)
    ).all()

    summary = {r.direction: {"total": float(r.total), "count": r.cnt} for r in rows}
    return summary


def _serialize(tx) -> dict:
    return {
        "id": tx.id,
        "source": tx.source,
        "direction": tx.direction,
        "amount": float(tx.amount),
        "currency": tx.currency,
        "merchant": tx.merchant,
        "description": tx.description,
        "category_l1": tx.category_l1,
        "category_l2": tx.category_l2,
        "category_source": tx.category_source,
        "category_confidence": float(tx.category_confidence),
        "transaction_at": tx.transaction_at.isoformat(),
    }
