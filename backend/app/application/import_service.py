"""Orchestrates bill file upload, parsing, and async processing trigger."""
import os
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ImportNotFoundError, ParseError, UnsupportedFormatError
from app.infrastructure.parsers import registry as parser_registry
from app.infrastructure.persistence.repositories import transaction_repo as repo


def submit_import(db: Session, file_content: bytes, file_name: str, user_id: str) -> dict:
    """
    1. Save file to disk
    2. Auto-detect format
    3. Create import record
    4. Enqueue Celery task
    Returns import status dict.
    """
    if not file_content:
        raise ParseError("Empty file")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_import_id = str(uuid4())
    temp_file_path = upload_dir / f"{temp_import_id}_{file_name}"
    temp_file_path.write_bytes(file_content)

    try:
        parser = parser_registry.auto_detect_file(temp_file_path)
    except UnsupportedFormatError as e:
        temp_file_path.unlink(missing_ok=True)
        raise ParseError(str(e)) from e

    imp = repo.create_import(db, user_id, parser.source_type, file_name)
    actual_import_id = imp.id

    actual_file_path = upload_dir / f"{actual_import_id}_{file_name}"
    os.rename(temp_file_path, actual_file_path)

    from app.infrastructure.queue.import_tasks import process_bill_import
    process_bill_import.delay(actual_import_id, str(actual_file_path), user_id)

    return {
        "import_id": actual_import_id,
        "source": parser.source_type,
        "file_name": file_name,
        "status": "pending",
    }


def get_import_status(db: Session, import_id: str, user_id: str) -> dict | None:
    return repo.get_import_detail(db, import_id, user_id)



def delete_import(db: Session, import_id: str, user_id: str) -> dict:
    status = get_import_status(db, import_id, user_id)
    if not status:
        raise ImportNotFoundError(f"Import {import_id} not found")

    result = repo.delete_import(db, import_id, user_id)

    upload_dir = Path(settings.upload_dir)
    file_path = upload_dir / f"{import_id}_{status['file_name']}"
    file_path.unlink(missing_ok=True)

    return {
        "import_id": import_id,
        **result,
    }
