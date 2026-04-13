"""
Skill loader: dynamically discovers and loads skills from backend/skills/.

Public API:
    load_skill(skill_name: str) -> SkillRunner
"""
import logging
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import SkillMalformedError, SkillNotFoundError  # noqa: F401

logger = logging.getLogger(__name__)


@dataclass
class SkillResult:
    """Result returned by SkillRunner.run()."""

    structured_output: Any  # Validated Pydantic instance of output_schema class
    reasoning: str
    confidence: float


class SkillRunner:
    """Holds a loaded skill definition and can invoke it against an LLM client."""

    def __init__(
        self,
        skill_name: str,
        system_prompt: str,
        input_schema_class: type,
        output_schema_class: type,
    ) -> None:
        self._skill_name = skill_name
        self._system_prompt = system_prompt
        self._input_schema_class = input_schema_class
        self._output_schema_class = output_schema_class

    def run(self, llm_client: Any, input_data: Any) -> SkillResult:
        """Call the LLM with the skill's system prompt and return a SkillResult."""
        raise NotImplementedError("Wave 1 (plan 02) implements this")


def load_skill(skill_name: str) -> SkillRunner:
    """
    Load a named skill from backend/skills/.

    Raises SkillNotFoundError if the skill directory is missing.
    Raises SkillMalformedError if required files or classes are absent or malformed.
    """
    raise NotImplementedError("Wave 1 (plan 02) implements this")
