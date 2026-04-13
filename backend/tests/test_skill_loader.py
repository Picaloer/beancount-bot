"""
Unit tests for Phase 2 skill loader (SKILL-02).
All tests in this file must FAIL (RED) before Wave 1 implementation.
"""
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.core.exceptions import SkillMalformedError, SkillNotFoundError
from app.infrastructure.ai.base import LLMCompletion, LLMMessage, LLMUsage
from app.infrastructure.skills.loader import SkillResult, SkillRunner, load_skill

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

REAL_SKILL_NAME = "cross-channel-dedup"


@dataclass
class MockLLMClient:
    """Duck-typed LLMAdapter for unit tests — no real HTTP calls."""

    response_text: str

    def complete(self, messages: list[LLMMessage], system: str = "") -> LLMCompletion:
        return LLMCompletion(text=self.response_text, usage=LLMUsage())


def _make_minimal_skill(base: Path, skill_name: str, *, has_skill_md: bool = True,
                         has_input_schema: bool = True, has_output_schema: bool = True,
                         input_class_name: str | None = None) -> Path:
    """Create a minimal skill directory structure under base/skill_name/."""
    pascal = "".join(part.capitalize() for part in skill_name.split("-"))
    expected_input_class = input_class_name if input_class_name is not None else f"{pascal}Input"
    skill_dir = base / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    if has_skill_md:
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            f"name: {skill_name}\n"
            "description: A minimal test skill.\n"
            "---\n\n"
            "## Purpose\n\nTest skill.\n\n"
            "## System Prompt\n\n```\nYou are a test assistant.\n```\n\n"
            "## Input\n\nSee input_schema.py.\n\n"
            "## Output\n\nSee output_schema.py.\n\n"
            "## Usage Example\n\nNone.\n"
        )
    if has_input_schema:
        (skill_dir / "input_schema.py").write_text(
            "from pydantic import BaseModel\n\n"
            f"class {expected_input_class}(BaseModel):\n"
            "    pass\n"
        )
    if has_output_schema:
        pascal_output = f"{pascal}Output"
        (skill_dir / "output_schema.py").write_text(
            "from pydantic import BaseModel\n\n"
            f"class {pascal_output}(BaseModel):\n"
            "    pass\n"
        )
    return skill_dir


# ---------------------------------------------------------------------------
# Tests: load_skill() — happy path
# ---------------------------------------------------------------------------

def test_load_skill_returns_runner():
    """load_skill('cross-channel-dedup') must return a SkillRunner instance."""
    runner = load_skill(REAL_SKILL_NAME)
    assert isinstance(runner, SkillRunner)


def test_load_skill_discovery_no_code_changes(tmp_path):
    """
    A new skill directory is discoverable by load_skill() without changing loader code.
    Uses tmp_path + monkeypatches the skills root to an isolated directory.
    """
    import app.infrastructure.skills.loader as loader_module

    _make_minimal_skill(tmp_path, "minimal-test-skill")

    with patch.object(loader_module, "_SKILLS_ROOT", tmp_path):
        runner = load_skill("minimal-test-skill")

    assert isinstance(runner, SkillRunner)


# ---------------------------------------------------------------------------
# Tests: load_skill() — error paths
# ---------------------------------------------------------------------------

def test_load_skill_not_found():
    """load_skill() raises SkillNotFoundError for a non-existent skill directory."""
    with pytest.raises(SkillNotFoundError) as exc_info:
        load_skill("no-such-skill")
    assert exc_info.value.skill_name == "no-such-skill"


def test_load_skill_missing_skill_md(tmp_path):
    """Skill directory exists but SKILL.md is absent → SkillMalformedError."""
    import app.infrastructure.skills.loader as loader_module

    _make_minimal_skill(tmp_path, "no-md-skill", has_skill_md=False)

    with patch.object(loader_module, "_SKILLS_ROOT", tmp_path):
        with pytest.raises(SkillMalformedError) as exc_info:
            load_skill("no-md-skill")
    assert exc_info.value.skill_name == "no-md-skill"


def test_load_skill_missing_input_schema(tmp_path):
    """Skill directory exists but input_schema.py is absent → SkillMalformedError."""
    import app.infrastructure.skills.loader as loader_module

    _make_minimal_skill(tmp_path, "no-input-skill", has_input_schema=False)

    with patch.object(loader_module, "_SKILLS_ROOT", tmp_path):
        with pytest.raises(SkillMalformedError) as exc_info:
            load_skill("no-input-skill")
    assert exc_info.value.skill_name == "no-input-skill"


def test_load_skill_missing_output_schema(tmp_path):
    """Skill directory exists but output_schema.py is absent → SkillMalformedError."""
    import app.infrastructure.skills.loader as loader_module

    _make_minimal_skill(tmp_path, "no-output-skill", has_output_schema=False)

    with patch.object(loader_module, "_SKILLS_ROOT", tmp_path):
        with pytest.raises(SkillMalformedError) as exc_info:
            load_skill("no-output-skill")
    assert exc_info.value.skill_name == "no-output-skill"


def test_load_skill_missing_class(tmp_path):
    """
    Schema file exists but the expected class (e.g. WrongNameInput) is absent
    → SkillMalformedError.
    """
    import app.infrastructure.skills.loader as loader_module

    # Provide wrong class name in input_schema.py (file exists, class name wrong)
    _make_minimal_skill(
        tmp_path,
        "bad-class-skill",
        input_class_name="WrongClassName",  # forces mismatch
    )

    with patch.object(loader_module, "_SKILLS_ROOT", tmp_path):
        with pytest.raises(SkillMalformedError) as exc_info:
            load_skill("bad-class-skill")
    assert exc_info.value.skill_name == "bad-class-skill"


def test_load_skill_validates_name():
    """
    Skill names with path-traversal characters or uppercase raise SkillNotFoundError
    (name validation fails before any filesystem operation).
    """
    with pytest.raises(SkillNotFoundError):
        load_skill("../etc/passwd")


# ---------------------------------------------------------------------------
# Tests: SkillRunner.run() — happy path
# ---------------------------------------------------------------------------

def test_skill_runner_run_returns_result():
    """
    SkillRunner.run() with a valid JSON envelope returns a SkillResult with
    structured_output (CrossChannelDedupOutput), reasoning (str), confidence (float).
    """
    runner = load_skill(REAL_SKILL_NAME)

    # CrossChannelDedupOutput is an empty BaseModel (pass body), so {} is valid
    valid_response = json.dumps({
        "output": {},
        "reasoning": "No duplicates found in this test.",
        "confidence": 0.9,
    })
    result = runner.run(MockLLMClient(valid_response), {})

    assert isinstance(result, SkillResult)
    assert isinstance(result.reasoning, str)
    assert isinstance(result.confidence, float)
    # structured_output must be a Pydantic model instance (not raw dict)
    from pydantic import BaseModel
    assert isinstance(result.structured_output, BaseModel)


# ---------------------------------------------------------------------------
# Tests: SkillRunner.run() — error paths
# ---------------------------------------------------------------------------

def test_skill_runner_invalid_json():
    """SkillRunner.run() raises SkillMalformedError when the LLM returns non-JSON."""
    runner = load_skill(REAL_SKILL_NAME)

    with pytest.raises(SkillMalformedError):
        runner.run(MockLLMClient("this is not JSON at all"), {})


def test_skill_runner_schema_validation_failure():
    """
    SkillRunner.run() raises SkillMalformedError when the LLM output envelope is
    valid JSON but the 'output' value fails schema validation.

    Uses a custom skill with a required field to force a validation failure.
    """
    # Build an in-memory SkillRunner with a strict output schema
    from pydantic import BaseModel

    class StrictOutput(BaseModel):
        required_field: str  # will fail validation if absent

    runner = SkillRunner(
        skill_name="strict-test",
        system_prompt="test",
        input_schema_class=StrictOutput,  # input class doesn't matter here
        output_schema_class=StrictOutput,
    )

    # Provide an output missing the required_field
    bad_response = json.dumps({
        "output": {},   # missing required_field
        "reasoning": "test",
        "confidence": 0.5,
    })

    with pytest.raises(SkillMalformedError):
        runner.run(MockLLMClient(bad_response), {})
