"""
Skill loader: dynamically discovers and loads skills from backend/skills/.

SECURITY NOTE: load_skill() accepts only kebab-case names matching [a-z0-9-]+.
Skills are first-party repository files only. Do NOT expose load_skill() to
untrusted external input — exec_module is called on skill schema .py files.

Public API:
    load_skill(skill_name: str) -> SkillRunner
"""
import importlib.util
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import SkillMalformedError, SkillNotFoundError
from app.infrastructure.ai.base import LLMMessage

logger = logging.getLogger(__name__)

# Resolved once at import time. Path arithmetic (verified in 02-RESEARCH.md):
# loader.py   = backend/app/infrastructure/skills/loader.py
# parents[0]  = backend/app/infrastructure/skills/
# parents[1]  = backend/app/infrastructure/
# parents[2]  = backend/app/
# parents[3]  = backend/
_SKILLS_ROOT: Path = Path(__file__).resolve().parents[3] / "skills"

# Skill names must be lower-kebab-case only — guards against path traversal.
_SKILL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

# Instructions appended to every skill system prompt so the LLM returns the
# three-field envelope that SkillRunner.run() parses.
_ENVELOPE_INSTRUCTIONS = """

Return your response as a JSON object with exactly these three top-level keys:
{
  "output": { ... },
  "reasoning": "your explanation as a plain string",
  "confidence": 0.0
}
"output" must be a JSON object matching the output schema described above.
"reasoning" must be a plain string.
"confidence" must be a number between 0.0 and 1.0.
Do not include any text, markdown, or code fences outside the JSON object.
"""


# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------


@dataclass
class SkillResult:
    """Returned by SkillRunner.run()."""

    structured_output: Any  # Validated Pydantic instance of the skill's output_schema class
    reasoning: str
    confidence: float


# ---------------------------------------------------------------------------
# SkillRunner
# ---------------------------------------------------------------------------


class SkillRunner:
    """
    Holds a loaded skill definition.  Call .run(llm_client, input_data) to invoke it.
    SkillRunner instances are logically immutable — do not add mutable state.
    """

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
        """
        Call the LLM with the skill's system prompt and return a SkillResult.

        Args:
            llm_client: Any object satisfying the LLMAdapter Protocol.
            input_data: A dict or Pydantic model instance to serialize as user message.

        Raises:
            SkillMalformedError: If the LLM returns non-JSON or output fails schema validation.
        """
        if isinstance(input_data, dict):
            user_content = json.dumps(input_data, ensure_ascii=False)
        else:
            user_content = json.dumps(input_data.model_dump(), ensure_ascii=False)

        full_system = self._system_prompt + _ENVELOPE_INSTRUCTIONS
        completion = llm_client.complete(
            messages=[LLMMessage(role="user", content=user_content)],
            system=full_system,
        )
        structured_output, reasoning, confidence = _parse_llm_response(
            self._skill_name, completion.text, self._output_schema_class
        )
        return SkillResult(
            structured_output=structured_output,
            reasoning=reasoning,
            confidence=confidence,
        )


# ---------------------------------------------------------------------------
# Public loader
# ---------------------------------------------------------------------------


def load_skill(skill_name: str) -> SkillRunner:
    """
    Load a named skill from backend/skills/.

    Args:
        skill_name: Kebab-case directory name, e.g. "cross-channel-dedup".
                    Must match [a-z0-9][a-z0-9-]* — path traversal is rejected.

    Returns:
        A SkillRunner ready to call .run(llm_client, input_data).

    Raises:
        SkillNotFoundError: If skill_name is invalid or the directory does not exist.
        SkillMalformedError: If required files or classes are absent or malformed.
    """
    # Security: validate before any filesystem operation
    if not _SKILL_NAME_RE.fullmatch(skill_name):
        raise SkillNotFoundError(skill_name)

    skill_dir = _SKILLS_ROOT / skill_name
    if not skill_dir.is_dir():
        raise SkillNotFoundError(skill_name)

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        raise SkillMalformedError(skill_name, "missing SKILL.md")

    _, system_prompt = _parse_skill_md(skill_name, skill_md_path.read_text())

    pascal = _kebab_to_pascal(skill_name)
    input_cls = _load_schema_class(skill_name, "input_schema.py", f"{pascal}Input")
    output_cls = _load_schema_class(skill_name, "output_schema.py", f"{pascal}Output")

    logger.debug("Loaded skill %r from %s", skill_name, skill_dir)
    return SkillRunner(
        skill_name=skill_name,
        system_prompt=system_prompt,
        input_schema_class=input_cls,
        output_schema_class=output_cls,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _kebab_to_pascal(name: str) -> str:
    """'cross-channel-dedup' -> 'CrossChannelDedup'."""
    return "".join(part.capitalize() for part in name.split("-"))


def _load_schema_class(skill_name: str, schema_file: str, class_name: str) -> type:
    """
    Load a Pydantic class from a skill's schema file by absolute path.

    Uses importlib.util.spec_from_file_location so kebab-named directories
    (invalid Python identifiers) are handled without sys.path manipulation.
    """
    file_path = _SKILLS_ROOT / skill_name / schema_file
    if not file_path.exists() or file_path.suffix != ".py":
        raise SkillMalformedError(skill_name, f"missing {schema_file}")

    snake_name = skill_name.replace("-", "_")
    module_name = f"skills.{snake_name}.{schema_file.removesuffix('.py')}"

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise SkillMalformedError(skill_name, f"cannot load {schema_file} (spec is None)")

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    try:
        return getattr(mod, class_name)
    except AttributeError:
        raise SkillMalformedError(
            skill_name, f"{schema_file} is missing expected class {class_name!r}"
        )


def _parse_skill_md(skill_name: str, text: str) -> tuple[dict[str, str], str]:
    """
    Parse SKILL.md front matter and extract the system prompt fenced block.

    Returns:
        (front_matter_dict, system_prompt_text)

    Raises:
        SkillMalformedError: If front matter is missing or malformed.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillMalformedError(skill_name, "SKILL.md missing YAML front matter opening ---")

    try:
        fm_end = lines[1:].index("---") + 1
    except ValueError:
        raise SkillMalformedError(skill_name, "SKILL.md YAML front matter not closed with ---")

    fm: dict[str, str] = {}
    for line in lines[1:fm_end]:
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()

    # Extract system prompt from the fenced code block inside ## System Prompt section.
    # Pattern: ## System Prompt\n...\n```[lang]\n<content>\n```
    match = re.search(r"## System Prompt\s*\n+```[^\n]*\n(.*?)```", text, re.DOTALL)
    system_prompt = match.group(1).strip() if match else ""

    return fm, system_prompt


def _parse_llm_response(
    skill_name: str, text: str, output_schema_class: type
) -> tuple[Any, str, float]:
    """
    Parse the LLM three-field JSON envelope and validate the 'output' field.

    Returns:
        (structured_output, reasoning, confidence)

    Raises:
        SkillMalformedError: If text is not valid JSON or output fails schema validation.
    """
    text = text.strip()

    # Strip markdown code fences — same pattern as classification_agent.py
    if "```" in text:
        parts = text.split("```")
        for i in range(1, len(parts), 2):
            candidate = parts[i]
            if candidate.startswith("json"):
                candidate = candidate[4:]
            text = candidate.strip()
            break

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SkillMalformedError(skill_name, f"LLM returned non-JSON: {exc}") from exc

    try:
        structured_output = output_schema_class.model_validate(data.get("output", {}))
    except ValidationError as exc:
        raise SkillMalformedError(
            skill_name, f"LLM output failed schema validation: {exc}"
        ) from exc

    reasoning = str(data.get("reasoning", ""))
    confidence = float(data.get("confidence", 0.0))
    return structured_output, reasoning, confidence
