from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.config import settings
from app.domain.classification.category_tree import CATEGORY_TREE, is_valid_l1
from app.infrastructure.persistence.database import get_db
from app.infrastructure.persistence.repositories import transaction_repo as repo

router = APIRouter(prefix="/categories", tags=["categories"])


class RuleCreate(BaseModel):
    match_value: str   # keyword to match
    category_l1: str
    category_l2: str | None = None
    match_field: str = "merchant"
    priority: int = 10


class RuleSuggestionCreate(BaseModel):
    match_field: str = "merchant"
    match_value: str
    category_l1: str
    category_l2: str | None = None
    confidence: float = 0.8
    source: str = "manual_feedback"
    reason: str | None = None
    evidence_count: int = 1
    sample_transactions: list[dict] = Field(default_factory=list)



def _serialize_rule(rule) -> dict:
    return {
        "id": rule.id,
        "match_field": rule.match_field,
        "match_value": rule.match_value,
        "category_l1": rule.category_l1,
        "category_l2": rule.category_l2,
        "priority": rule.priority,
    }



def _serialize_rule_suggestion(suggestion) -> dict:
    return {
        "id": suggestion.id,
        "match_field": suggestion.match_field,
        "match_value": suggestion.match_value,
        "category_l1": suggestion.category_l1,
        "category_l2": suggestion.category_l2,
        "confidence": float(suggestion.confidence),
        "source": suggestion.source,
        "status": suggestion.status,
        "reason": suggestion.reason,
        "evidence_count": suggestion.evidence_count,
        "sample_transactions": suggestion.sample_transactions,
        "created_at": suggestion.created_at.isoformat(),
        "resolved_at": suggestion.resolved_at.isoformat() if suggestion.resolved_at else None,
    }


@router.get("")
def get_category_tree():
    """Return full two-level category taxonomy."""
    return {
        "tree": [
            {"category_l1": l1, "subcategories": subs}
            for l1, subs in CATEGORY_TREE.items()
        ]
    }


@router.get("/rules")
def list_rules(db: Session = Depends(get_db)):
    """List user-defined classification rules."""
    from sqlalchemy import select
    from app.infrastructure.persistence.models.orm_models import CategoryRuleORM

    rows = db.scalars(
        select(CategoryRuleORM)
        .where(CategoryRuleORM.user_id == settings.default_user_id)
        .order_by(CategoryRuleORM.priority.desc())
    ).all()

    return [
        _serialize_rule(r)
        for r in rows
    ]


@router.post("/rules", status_code=201)
def create_rule(body: RuleCreate, db: Session = Depends(get_db)):
    """Create a new classification rule."""
    from app.domain.classification.category_tree import get_l2_options
    from app.infrastructure.persistence.models.orm_models import CategoryRuleORM
    from app.infrastructure.persistence.repositories.transaction_repo import ensure_user

    body.match_value = body.match_value.strip()
    if not body.match_value:
        raise HTTPException(status_code=400, detail="Rule keyword cannot be empty")
    if body.match_field not in {"merchant", "description", "any"}:
        raise HTTPException(status_code=400, detail="match_field must be merchant, description, or any")
    if not is_valid_l1(body.category_l1):
        raise HTTPException(status_code=400, detail="Invalid category_l1")
    if body.category_l2 and body.category_l2 not in get_l2_options(body.category_l1):
        raise HTTPException(status_code=400, detail="Invalid category_l2 for category_l1")

    ensure_user(db, settings.default_user_id)
    rule = CategoryRuleORM(
        id=str(uuid4()),
        user_id=settings.default_user_id,
        match_field=body.match_field,
        match_value=body.match_value,
        category_l1=body.category_l1,
        category_l2=body.category_l2,
        priority=body.priority,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _serialize_rule(rule)


@router.get("/rule-suggestions")
def list_rule_suggestions(status: str = "pending", db: Session = Depends(get_db)):
    rows = repo.list_rule_suggestions(db, settings.default_user_id, status=status)
    return [_serialize_rule_suggestion(row) for row in rows]


@router.post("/rule-suggestions", status_code=201)
def create_rule_suggestion(body: RuleSuggestionCreate, db: Session = Depends(get_db)):
    from app.domain.classification.category_tree import get_l2_options

    body.match_value = body.match_value.strip()
    if not body.match_value:
        raise HTTPException(status_code=400, detail="Suggestion keyword cannot be empty")
    if body.match_field not in {"merchant", "description", "any"}:
        raise HTTPException(status_code=400, detail="match_field must be merchant, description, or any")
    if not is_valid_l1(body.category_l1):
        raise HTTPException(status_code=400, detail="Invalid category_l1")
    if body.category_l2 and body.category_l2 not in get_l2_options(body.category_l1):
        raise HTTPException(status_code=400, detail="Invalid category_l2 for category_l1")

    suggestion = repo.save_rule_suggestion(
        db,
        user_id=settings.default_user_id,
        match_field=body.match_field,
        match_value=body.match_value,
        category_l1=body.category_l1,
        category_l2=body.category_l2,
        confidence=body.confidence,
        source=body.source,
        reason=body.reason,
        evidence_count=body.evidence_count,
        sample_transactions=body.sample_transactions,
    )
    return _serialize_rule_suggestion(suggestion)


@router.post("/rule-suggestions/generate")
def generate_rule_suggestions(db: Session = Depends(get_db)):
    rows = repo.generate_rule_suggestions_from_history(db, settings.default_user_id)
    return {
        "count": len(rows),
        "items": [_serialize_rule_suggestion(row) for row in rows],
    }


@router.post("/rule-suggestions/{suggestion_id}/approve", status_code=201)
def approve_rule_suggestion(suggestion_id: str, db: Session = Depends(get_db)):
    try:
        rule = repo.approve_rule_suggestion(db, suggestion_id, settings.default_user_id)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_rule(rule)


@router.post("/rule-suggestions/{suggestion_id}/reject")
def reject_rule_suggestion(suggestion_id: str, db: Session = Depends(get_db)):
    try:
        suggestion = repo.reject_rule_suggestion(db, suggestion_id, settings.default_user_id)
    except ValueError as exc:
        if "not found" in str(exc):
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_rule_suggestion(suggestion)


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    from app.infrastructure.persistence.models.orm_models import CategoryRuleORM

    rule = db.get(CategoryRuleORM, rule_id)
    if not rule or rule.user_id != settings.default_user_id:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
