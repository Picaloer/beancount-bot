from app.core.config import settings
from app.infrastructure.ai.base import LLMAdapter


def create_llm_client() -> LLMAdapter:
    """Return the configured LLM adapter based on settings.llm_provider."""
    if settings.llm_provider == "deepseek":
        from app.infrastructure.ai.deepseek_client import DeepSeekClient
        return DeepSeekClient()
    from app.infrastructure.ai.claude_client import ClaudeClient
    return ClaudeClient()
