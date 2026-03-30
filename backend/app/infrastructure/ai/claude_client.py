import logging

import anthropic

from app.core.config import settings
from app.core.exceptions import LLMError
from app.infrastructure.ai.base import LLMAdapter, LLMMessage

logger = logging.getLogger(__name__)


class ClaudeClient(LLMAdapter):
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.llm_model

    def complete(self, messages: list[LLMMessage], system: str = "") -> str:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system or anthropic.NOT_GIVEN,
                messages=[{"role": m.role, "content": m.content} for m in messages],
            )
            return response.content[0].text
        except anthropic.APIError as e:
            logger.error("Claude API error: %s", e)
            raise LLMError(str(e)) from e
