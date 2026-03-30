from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application import budget_service
from app.core.config import settings
from app.infrastructure.persistence.database import get_db

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/{year_month}")
def get_budget_plan(
    year_month: str,
    regenerate: bool = False,
    db: Session = Depends(get_db),
):
    """Get or generate a monthly budget plan."""
    try:
        year, month = year_month.split("-")
        assert len(year) == 4 and 1 <= int(month) <= 12
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid year_month format. Use YYYY-MM")

    return budget_service.get_or_generate_budget_plan(
        db,
        settings.default_user_id,
        year_month,
        regenerate=regenerate,
    )
