from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    success: bool
    data: Any = None
    error: str = ""


class AIAgent(ABC):
    agent_id: str
    description: str

    @abstractmethod
    def run(self, **kwargs) -> AgentResult:
        """Execute the agent with given keyword arguments."""
