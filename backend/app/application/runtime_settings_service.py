from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.persistence.models.orm_models import RuntimeSettingORM
from app.infrastructure.persistence.repositories.transaction_repo import ensure_user


def get_runtime_settings(db: Session, user_id: str) -> RuntimeSettingORM:
    settings_row = db.scalar(select(RuntimeSettingORM).where(RuntimeSettingORM.user_id == user_id))
    if settings_row:
        return settings_row

    ensure_user(db, user_id)
    settings_row = RuntimeSettingORM(
        id=str(uuid4()),
        user_id=user_id,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        anthropic_api_key=settings.anthropic_api_key,
        deepseek_api_key=settings.deepseek_api_key,
        llm_base_url="",
        llm_batch_size=settings.llm_batch_size,
        llm_max_concurrency=4,
    )
    db.add(settings_row)
    db.commit()
    db.refresh(settings_row)
    return settings_row


def update_runtime_settings(
    db: Session,
    user_id: str,
    *,
    llm_provider: str,
    llm_model: str,
    anthropic_api_key: str,
    deepseek_api_key: str,
    llm_base_url: str,
    llm_batch_size: int,
    llm_max_concurrency: int,
) -> RuntimeSettingORM:
    settings_row = get_runtime_settings(db, user_id)
    settings_row.llm_provider = llm_provider
    settings_row.llm_model = llm_model
    settings_row.anthropic_api_key = anthropic_api_key
    settings_row.deepseek_api_key = deepseek_api_key
    settings_row.llm_base_url = llm_base_url
    settings_row.llm_batch_size = llm_batch_size
    settings_row.llm_max_concurrency = llm_max_concurrency
    db.commit()
    db.refresh(settings_row)
    return settings_row
