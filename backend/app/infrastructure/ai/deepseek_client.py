import logging

import openai

from app.core.config import settings
from app.core.exceptions import LLMError
from app.infrastructure.ai.base import LLMAdapter, LLMMessage

logger = logging.getLogger(__name__)


class DeepSeekClient(LLMAdapter):
    def __init__(self) -> None:
        self._client = openai.OpenAI(
            api_key=settings.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
        self._model = settings.llm_model 

    def complete(self, messages: list[LLMMessage], system: str = "") -> str:
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
            return response.choices[0].message.content
        except openai.APIError as e:
            logger.error("DeepSeek API error: %s", e)
            raise LLMError(str(e)) from e
