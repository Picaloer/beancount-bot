from typing import Protocol

from app.infrastructure.ai.base import LLMCompletion, LLMMessage


class LLMAdapter(Protocol):
    def complete(self, messages: list[LLMMessage], system: str = "") -> LLMCompletion:
        """Send messages and return text plus token usage."""
