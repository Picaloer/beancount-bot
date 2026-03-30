from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str   # 'user' | 'assistant' | 'system'
    content: str


class LLMAdapter(ABC):
    @abstractmethod
    def complete(self, messages: list[LLMMessage], system: str = "") -> str:
        """Send messages and return the assistant's text response."""
