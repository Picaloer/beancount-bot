from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMMessage:
    role: str   # 'user' | 'assistant' | 'system'
    content: str


@dataclass
class LLMUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMCompletion:
    text: str
    usage: LLMUsage


class LLMAdapter(Protocol):
    def complete(self, messages: list[LLMMessage], system: str = "") -> LLMCompletion:
        """Send messages and return text plus token usage."""
