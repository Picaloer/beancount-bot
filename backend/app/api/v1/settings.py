from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.runtime_settings_service import get_runtime_settings, update_runtime_settings
from app.core.config import settings
from app.core.timezone import isoformat_beijing
from app.infrastructure.persistence.database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])


class RuntimeSettingsUpdate(BaseModel):
    llm_provider: str = Field(pattern="^(claude|deepseek)$")
    llm_model: str = Field(min_length=1, max_length=100)
    anthropic_api_key: str = ""
    deepseek_api_key: str = ""
    llm_base_url: str = ""
    llm_batch_size: int = Field(ge=1, le=200)
    llm_max_concurrency: int = Field(ge=1, le=32)


class RuntimeSettingsResponse(BaseModel):
    llm_provider: str
    llm_model: str
    anthropic_api_key: str
    deepseek_api_key: str
    llm_base_url: str
    llm_batch_size: int
    llm_max_concurrency: int
    created_at: str
    updated_at: str
    effective_provider: str
    effective_model: str


class RuntimeSettingsUpdateResult(RuntimeSettingsResponse):
    pass


def _mask_secret(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    if len(stripped) <= 8:
        return "*" * len(stripped)
    return f"{stripped[:4]}{'*' * (len(stripped) - 8)}{stripped[-4:]}"


def _serialize_runtime_settings(runtime, *, reveal_secrets: bool = False) -> dict:
    return {
        "llm_provider": runtime.llm_provider,
        "llm_model": runtime.llm_model,
        "anthropic_api_key": runtime.anthropic_api_key if reveal_secrets else _mask_secret(runtime.anthropic_api_key),
        "deepseek_api_key": runtime.deepseek_api_key if reveal_secrets else _mask_secret(runtime.deepseek_api_key),
        "llm_base_url": runtime.llm_base_url,
        "llm_batch_size": runtime.llm_batch_size,
        "llm_max_concurrency": runtime.llm_max_concurrency,
        "created_at": isoformat_beijing(runtime.created_at),
        "updated_at": isoformat_beijing(runtime.updated_at),
        "effective_provider": runtime.llm_provider or settings.llm_provider,
        "effective_model": runtime.llm_model or settings.llm_model,
    }


@router.get("/runtime", response_model=RuntimeSettingsResponse)
def get_runtime_config(db: Session = Depends(get_db)):
    runtime = get_runtime_settings(db, settings.default_user_id)
    return _serialize_runtime_settings(runtime)


@router.put("/runtime", response_model=RuntimeSettingsUpdateResult)
def update_runtime_config(body: RuntimeSettingsUpdate, db: Session = Depends(get_db)):
    if body.llm_provider == "claude" and not body.anthropic_api_key.strip():
        raise HTTPException(status_code=400, detail="Anthropic API key is required when provider is claude")
    if body.llm_provider == "deepseek" and not body.deepseek_api_key.strip():
        raise HTTPException(status_code=400, detail="DeepSeek API key is required when provider is deepseek")

    runtime = update_runtime_settings(
        db,
        settings.default_user_id,
        llm_provider=body.llm_provider,
        llm_model=body.llm_model.strip(),
        anthropic_api_key=body.anthropic_api_key.strip(),
        deepseek_api_key=body.deepseek_api_key.strip(),
        llm_base_url=body.llm_base_url.strip(),
        llm_batch_size=body.llm_batch_size,
        llm_max_concurrency=body.llm_max_concurrency,
    )
    return _serialize_runtime_settings(runtime)
