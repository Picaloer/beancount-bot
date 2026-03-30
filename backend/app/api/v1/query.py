from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application import query_service
from app.core.config import settings
from app.infrastructure.persistence.database import get_db

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str


@router.post("")
def ask_question(body: QueryRequest, db: Session = Depends(get_db)):
    """Answer a natural-language finance question using deterministic query parsing."""
    try:
        return query_service.answer_question(db, settings.default_user_id, body.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
