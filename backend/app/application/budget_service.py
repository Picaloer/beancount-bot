"""Budget planning and recommendation services."""
from statistics import mean

from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories import transaction_repo as repo


MIN_BUDGET_AMOUNT = 50.0
DEFAULT_BUFFER_RATIO = 1.08
MAX_BUFFER_RATIO = 1.25
WINDOW_MONTHS = 6


def get_or_generate_budget_plan(
    db: Session,
    user_id: str,
    year_month: str,
    regenerate: bool = False,
) -> dict:
    existing = [] if regenerate else repo.get_budget_plan(db, user_id, year_month)
    if existing:
        return _serialize_budget_plan(year_month, existing, generated=False)

    generated_items = _build_budget_recommendations(db, user_id, year_month)
    rows = repo.replace_budget_plan(db, user_id, year_month, generated_items)
    return _serialize_budget_plan(year_month, rows, generated=True)



def _build_budget_recommendations(db: Session, user_id: str, year_month: str) -> list[dict[str, float | str]]:
    trend_data = repo.get_category_trends(db, user_id, year_month, months=WINDOW_MONTHS, limit=8)
    current_stats = repo.get_monthly_stats(db, user_id, year_month)
    current_breakdown = {
        item["category_l1"]: float(item["amount"])
        for item in current_stats["category_breakdown"]
    }

    month_points = trend_data["points"]
    current_point = next((point for point in month_points if point["year_month"] == year_month), None)

    recommendations: list[dict[str, float | str]] = []
    for category in trend_data["categories"]:
        history = [
            float(point.get(category, 0) or 0)
            for point in month_points
            if point["year_month"] != year_month and float(point.get(category, 0) or 0) > 0
        ]

        current_spent = float(current_breakdown.get(category, 0.0))
        current_month_amount = float(current_point.get(category, 0) or 0) if current_point else current_spent
        baseline = mean(history) if history else current_month_amount or current_spent
        peak = max(history) if history else baseline
        growth = ((current_month_amount - baseline) / baseline) if baseline else 0.0
        growth = max(0.0, min(growth, MAX_BUFFER_RATIO - 1))
        buffer_ratio = min(MAX_BUFFER_RATIO, DEFAULT_BUFFER_RATIO + growth * 0.5)
        recommended = max(MIN_BUDGET_AMOUNT, round(max(baseline, peak * 0.92) * buffer_ratio, 2))
        usage_ratio = round(current_spent / recommended, 4) if recommended else 0.0

        recommendations.append(
            {
                "category_l1": category,
                "amount": recommended,
                "spent": round(current_spent, 2),
                "usage_ratio": usage_ratio,
                "source": "ai",
            }
        )

    if not recommendations and current_breakdown:
        for category, amount in sorted(current_breakdown.items(), key=lambda item: item[1], reverse=True)[:5]:
            recommended = max(MIN_BUDGET_AMOUNT, round(amount * DEFAULT_BUFFER_RATIO, 2))
            recommendations.append(
                {
                    "category_l1": category,
                    "amount": recommended,
                    "spent": round(amount, 2),
                    "usage_ratio": round(amount / recommended, 4) if recommended else 0.0,
                    "source": "ai",
                }
            )

    return recommendations



def _serialize_budget_plan(year_month: str, rows, generated: bool) -> dict:
    items = []
    total_budget = 0.0
    total_spent = 0.0

    for row in rows:
        budget_amount = round(float(row.amount), 2)
        spent_amount = round(float(row.spent), 2)
        usage_ratio = round(float(row.usage_ratio), 4)
        status = "overspent" if usage_ratio >= 1 else "warning" if usage_ratio >= 0.8 else "healthy"
        items.append(
            {
                "id": row.id,
                "category_l1": row.category_l1,
                "budget": budget_amount,
                "spent": spent_amount,
                "remaining": round(budget_amount - spent_amount, 2),
                "usage_ratio": usage_ratio,
                "usage_percentage": round(usage_ratio * 100, 1),
                "source": row.source,
                "status": status,
            }
        )
        total_budget += budget_amount
        total_spent += spent_amount

    items.sort(key=lambda item: item["budget"], reverse=True)
    total_usage_ratio = round(total_spent / total_budget, 4) if total_budget else 0.0

    return {
        "year_month": year_month,
        "generated": generated,
        "total_budget": round(total_budget, 2),
        "total_spent": round(total_spent, 2),
        "remaining": round(total_budget - total_spent, 2),
        "usage_ratio": total_usage_ratio,
        "usage_percentage": round(total_usage_ratio * 100, 1),
        "categories": items,
    }
