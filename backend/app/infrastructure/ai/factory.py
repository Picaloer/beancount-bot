from app.core.config import settings
from app.infrastructure.ai.base import LLMAdapter


def create_llm_client(
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> LLMAdapter:
    """Return the configured LLM adapter based on runtime settings."""
    llm_provider = provider or settings.llm_provider
    llm_model = model or settings.llm_model
    if llm_provider == "deepseek":
        from app.infrastructure.ai.deepseek_client import DeepSeekClient
        return DeepSeekClient(api_key=api_key, base_url=base_url, model=llm_model)
    from app.infrastructure.ai.claude_client import ClaudeClient
    return ClaudeClient(api_key=api_key, model=llm_model)
