from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.application import import_service
from app.core.config import settings
from app.core.exceptions import ImportNotFoundError, ParseError
from app.core.timezone import isoformat_beijing
from app.infrastructure.persistence.database import get_db

router = APIRouter(prefix="/bills", tags=["bills"])


@router.post("/import")
def import_bill(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and process a WeChat or Alipay bill CSV."""
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        result = import_service.submit_import(
            db=db,
            file_content=content,
            file_name=file.filename or "bill.csv",
            user_id=settings.default_user_id,
        )
    except ParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return result


@router.get("/import/{import_id}")
def get_import_status(import_id: str, db: Session = Depends(get_db)):
    """Poll import processing status."""
    status = import_service.get_import_status(db, import_id, settings.default_user_id)
    if not status:
        raise HTTPException(status_code=404, detail="Import not found")
    return status


@router.get("/import/{import_id}/detail")
def get_import_detail(import_id: str, db: Session = Depends(get_db)):
    """Get rich import detail for the current user."""
    detail = import_service.get_import_status(db, import_id, settings.default_user_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Import not found")
    return detail


@router.delete("/import/{import_id}")
def delete_import(import_id: str, db: Session = Depends(get_db)):
    """Delete an import and all generated data."""
    try:
        return import_service.delete_import(db, import_id, settings.default_user_id)
    except ImportNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/imports")
def list_imports(db: Session = Depends(get_db)):
    """List all imports for the current user."""
    from sqlalchemy import select
    from app.infrastructure.persistence.models.orm_models import BillImportORM

    rows = db.scalars(
        select(BillImportORM)
        .where(BillImportORM.user_id == settings.default_user_id)
        .order_by(BillImportORM.imported_at.desc())
        .limit(20)
    ).all()

    return [
        {
            "import_id": r.id,
            "source": r.source,
            "file_name": r.file_name,
            "status": r.status,
            "row_count": r.row_count,
            "total_rows": r.total_rows,
            "processed_rows": r.processed_rows,
            "llm_total_batches": r.llm_total_batches,
            "llm_completed_batches": r.llm_completed_batches,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "total_tokens": r.input_tokens + r.output_tokens,
            "stage_message": r.stage_message,
            "error_message": r.error_message,
            "imported_at": isoformat_beijing(r.imported_at),
            "started_at": isoformat_beijing(r.started_at) if r.started_at else None,
            "finished_at": isoformat_beijing(r.finished_at) if r.finished_at else None,
        }
        for r in rows
    ]
