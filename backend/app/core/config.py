from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/beancount_bot"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # LLM provider: "claude" | "deepseek"
    llm_provider: str = "claude"

    # Anthropic (used when llm_provider=claude)
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"

    # DeepSeek (used when llm_provider=deepseek)
    deepseek_api_key: str = ""
    # llm_model is reused; recommended DeepSeek value: deepseek-chat

    llm_batch_size: int = 20  # transactions per LLM call

    # App
    debug: bool = False
    upload_dir: str = "./uploads"
    # MVP 单用户模式，无需登录
    default_user_id: str = "00000000-0000-0000-0000-000000000001"

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url


settings = Settings()
