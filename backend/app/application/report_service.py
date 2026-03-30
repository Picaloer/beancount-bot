"""Monthly report generation with optional AI insight."""
import logging
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models.orm_models import MonthlyReportORM
from app.infrastructure.persistence.repositories import transaction_repo as repo

logger = logging.getLogger(__name__)


def get_or_generate_report(db: Session, user_id: str, year_month: str, regenerate: bool = False) -> dict:
    """
    Returns cached report if available, otherwise generates fresh.
    Set regenerate=True to force rebuild.
    """
    if not regenerate:
        cached = db.scalar(
            select(MonthlyReportORM).where(
                MonthlyReportORM.user_id == user_id,
                MonthlyReportORM.year_month == year_month,
            )
        )
        if cached:
            return {**cached.data, "ai_insight": cached.ai_insight, "cached": True}

    stats = repo.get_monthly_stats(db, user_id, year_month)

    # Attempt AI insight generation
    ai_insight = None
    try:
        from app.infrastructure.ai.factory import create_llm_client
        from app.infrastructure.ai.agents.insight_agent import InsightAgent

        # Load previous month stats for comparison
        year, month = map(int, year_month.split("-"))
        if month == 1:
            prev_ym = f"{year - 1}-12"
        else:
            prev_ym = f"{year}-{month - 1:02d}"

        prev_stats = repo.get_monthly_stats(db, user_id, prev_ym)
        prev_stats_arg = prev_stats if prev_stats.get("transaction_count", 0) > 0 else None

        agent = InsightAgent(create_llm_client())
        result = agent.run(monthly_stats=stats, prev_stats=prev_stats_arg)
        if result.success:
            ai_insight = result.data
    except Exception as e:
        logger.warning("Insight generation skipped: %s", e)

    # Upsert cache
    existing = db.scalar(
        select(MonthlyReportORM).where(
            MonthlyReportORM.user_id == user_id,
            MonthlyReportORM.year_month == year_month,
        )
    )
    if existing:
        existing.data = stats
        existing.ai_insight = ai_insight
    else:
        db.add(MonthlyReportORM(
            id=str(uuid4()),
            user_id=user_id,
            year_month=year_month,
            data=stats,
            ai_insight=ai_insight,
        ))
    db.commit()

    return {**stats, "ai_insight": ai_insight, "cached": False}


def list_available_months(db: Session, user_id: str) -> list[str]:
    """Returns sorted list of year-month strings that have transaction data."""
    from sqlalchemy import func
    from app.infrastructure.persistence.models.orm_models import TransactionORM

    rows = db.scalars(
        select(
            func.to_char(TransactionORM.transaction_at, "YYYY-MM")
        ).where(
            TransactionORM.user_id == user_id
        ).distinct().order_by(
            func.to_char(TransactionORM.transaction_at, "YYYY-MM").desc()
        )
    ).all()
    return list(rows)



def get_category_trends(db: Session, user_id: str, year_month: str, months: int = 6, limit: int = 5) -> dict:
    """Returns category expense trends for the selected month window."""
    return repo.get_category_trends(db, user_id, year_month, months=months, limit=limit)
