from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.config import settings
from app.domain.classification.category_tree import CATEGORY_TREE, is_valid_l1
from app.infrastructure.persistence.database import get_db

router = APIRouter(prefix="/categories", tags=["categories"])


class RuleCreate(BaseModel):
    match_value: str   # keyword to match
    category_l1: str
    category_l2: str | None = None
    match_field: str = "merchant"
    priority: int = 10



def _serialize_rule(rule) -> dict:
    return {
        "id": rule.id,
        "match_field": rule.match_field,
        "match_value": rule.match_value,
        "category_l1": rule.category_l1,
        "category_l2": rule.category_l2,
        "priority": rule.priority,
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


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: str, db: Session = Depends(get_db)):
    from app.infrastructure.persistence.models.orm_models import CategoryRuleORM

    rule = db.get(CategoryRuleORM, rule_id)
    if not rule or rule.user_id != settings.default_user_id:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
