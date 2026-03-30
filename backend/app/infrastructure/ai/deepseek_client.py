import logging

import openai

from app.core.config import settings
from app.core.exceptions import LLMError
from app.infrastructure.ai.base import LLMAdapter, LLMCompletion, LLMMessage, LLMUsage

logger = logging.getLogger(__name__)


class DeepSeekClient(LLMAdapter):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._client = openai.OpenAI(
            api_key=api_key or settings.deepseek_api_key,
            base_url=base_url or "https://api.deepseek.com",
        )
        self._model = model or settings.llm_model

    def complete(self, messages: list[LLMMessage], system: str = "") -> LLMCompletion:
        try:
            api_messages = []
            if system:
                api_messages.append({"role": "system", "content": system})
            api_messages.extend({"role": m.role, "content": m.content} for m in messages)

            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=4096,
                messages=api_messages,
            )
            usage = LLMUsage(
                input_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(response.usage, "completion_tokens", 0) or 0,
            )
            return LLMCompletion(text=response.choices[0].message.content or "", usage=usage)
        except openai.APIError as e:
            logger.error("DeepSeek API error: %s", e)
            raise LLMError(str(e)) from e
