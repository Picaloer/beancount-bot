import logging

import anthropic

from app.core.config import settings
from app.core.exceptions import LLMError
from app.infrastructure.ai.base import LLMAdapter, LLMCompletion, LLMMessage, LLMUsage

logger = logging.getLogger(__name__)


class ClaudeClient(LLMAdapter):
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._client = anthropic.Anthropic(api_key=api_key or settings.anthropic_api_key)
        self._model = model or settings.llm_model

    def complete(self, messages: list[LLMMessage], system: str = "") -> LLMCompletion:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system or anthropic.NOT_GIVEN,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            )
            usage = LLMUsage(
                input_tokens=getattr(response.usage, "input_tokens", 0) or 0,
                output_tokens=getattr(response.usage, "output_tokens", 0) or 0,
            )
            return LLMCompletion(text=response.content[0].text, usage=usage)
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            raise LLMError(str(e)) from e
