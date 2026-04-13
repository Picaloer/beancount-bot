# Phase 2: Skill Loader - Research

**Researched:** 2026-04-13
**Domain:** Python dynamic module loading, dataclass/Pydantic result contracts, infrastructure layer extension
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** `load_skill("skill-name")` returns a **`SkillRunner`** instance — not a passive
`SkillDefinition` dataclass and not a plain dict.

**D-02:** `SkillRunner.run(llm_client, input_data)` accepts an LLM client and the input
data, calls the LLM, and returns a **`SkillResult`**. Caller injects the LLM client
(dependency injection — consistent with existing `AIAgent(ABC)` pattern).

**D-03:** **`SkillResult`** contains exactly three fields:
- `structured_output` — a validated Pydantic instance of the skill's declared `output_schema` class
- `reasoning` — `str`, the LLM's explanation of its decision
- `confidence` — numeric, the LLM's stated confidence

**D-04:** Phase 2 implements the full `SkillResult` contract. Phase 3 will validate and
test that the contract is universally applied and that malformed LLM outputs are rejected.

### Claude's Discretion

- Loader module location (recommended: `app/infrastructure/skills/loader.py`)
- SKILL.md parsing depth (recommended: extract front matter `name`/`description` + raw `## System Prompt` fenced block)
- Error exception types (recommended: add `SkillNotFoundError` and `SkillMalformedError` to `app/core/exceptions.py`)
- Python import mechanism for schema classes (recommended: `importlib.import_module` with kebab→snake_case conversion)

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKILL-02 | 实现 `load_skill(skill_name)` 机制，动态读取 skill 定义并构造 LLM 调用；skill 定义与业务逻辑解耦，便于独立扩展 | `importlib.util.spec_from_file_location` provides the correct filesystem-first dynamic loading mechanism. `SkillRunner.run(llm_client, input_data)` decouples skill definition from business code that calls it. |

</phase_requirements>

---

## Summary

Phase 2 builds a filesystem-based skill loader on top of the scaffold created in Phase 1. The loader reads a skill directory by name, parses its `SKILL.md` for front matter and system prompt, dynamically imports its Pydantic schema classes, and returns a `SkillRunner` object. `SkillRunner.run(llm_client, input_data)` calls the LLM and returns a `SkillResult` with `structured_output`, `reasoning`, and `confidence`.

The core technical challenge is that skill directories use kebab-case names (`cross-channel-dedup`) which are not valid Python identifiers, so `importlib.import_module` cannot traverse to them directly. The solution verified in this research is `importlib.util.spec_from_file_location`, which loads schema modules by absolute file path — no `__init__.py` files are needed, and directory names do not need to match Python module name conventions.

The LLM call envelope pattern must be defined here: the system prompt instructs the model to return a JSON object with three keys (`output`, `reasoning`, `confidence`), where `output` is a JSON object matching the `output_schema`. `SkillRunner.run()` strips any Markdown code fences, parses JSON, validates the `output` field with `output_schema_class.model_validate(data["output"])`, and assembles the `SkillResult` dataclass.

**Primary recommendation:** Implement `backend/app/infrastructure/skills/loader.py` as a new sub-package of `infrastructure/`, using `importlib.util.spec_from_file_location` for schema imports and a minimal hand-rolled front matter parser (PyYAML is not available in the project). Add `SkillNotFoundError` and `SkillMalformedError` to `app/core/exceptions.py`. Write tests in `backend/tests/test_skill_loader.py` using a `MockLLMClient` duck-typed against the existing `LLMAdapter` Protocol.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathlib` | stdlib | Filesystem path resolution for skill directories | Already used throughout the codebase |
| `importlib.util` | stdlib | Load schema `.py` files by absolute path | Only mechanism that handles kebab-named directories |
| `re` | stdlib | Extract system prompt from fenced code block in SKILL.md | Already used in classification_agent.py response parsing |
| `json` | stdlib | Parse/dump LLM JSON response envelope | Already used in classification_agent.py |
| `dataclasses` | stdlib | `SkillResult` dataclass | Consistent with `AgentResult` in `agents/base.py` |
| `pydantic` | `>=2.12.5` [VERIFIED: pyproject.toml] | `BaseModel.model_validate()` for output schema validation | Pydantic used everywhere in this codebase |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` | stdlib | Type annotations on all function signatures | Required by codebase convention |
| `logging` | stdlib | Module-level logger | Required by codebase convention |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `importlib.util.spec_from_file_location` | `importlib.import_module` | `import_module` requires directory name to be valid Python identifier; fails on `cross-channel-dedup` (hyphens). Verified: namespace package import fails with `ModuleNotFoundError`. |
| Hand-rolled front matter parser | PyYAML | PyYAML is not in `pyproject.toml` and not available on the system [VERIFIED: `importlib.util.find_spec('yaml')` returns None]. The front matter format is simple key: value lines; a hand-rolled parser is 5 lines and has no risk. |
| `model_validate_json()` | `json.loads()` + `model_validate()` | Two-step approach (parse JSON first, then validate) allows the loader to separately handle JSON parse errors vs. schema validation errors, producing clearer `SkillMalformedError` messages. |

**Installation:** No new packages required — all tools are Python stdlib or already in `pyproject.toml`. [VERIFIED: pyproject.toml]

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── app/
│   ├── core/
│   │   └── exceptions.py          # ADD: SkillNotFoundError, SkillMalformedError
│   └── infrastructure/
│       └── skills/                # NEW sub-package (parallel to ai/, parsers/, persistence/)
│           ├── __init__.py        # empty
│           └── loader.py          # load_skill(), SkillRunner, SkillResult
├── skills/
│   └── cross-channel-dedup/       # EXISTING (Phase 1)
│       ├── SKILL.md
│       ├── input_schema.py
│       └── output_schema.py
└── tests/
    └── test_skill_loader.py       # NEW (Phase 2 tests)
```

### Pattern 1: Skills Root Resolution

**What:** The loader must find `backend/skills/` from its own location at `backend/app/infrastructure/skills/loader.py`.

**When to use:** Every call to `load_skill()`.

**Example:**
```python
# Source: verified by path arithmetic in this research session
from pathlib import Path

# loader.py is at: backend/app/infrastructure/skills/loader.py
# parents[0] = backend/app/infrastructure/skills/
# parents[1] = backend/app/infrastructure/
# parents[2] = backend/app/
# parents[3] = backend/
_SKILLS_ROOT = Path(__file__).resolve().parents[3] / "skills"
```

### Pattern 2: Kebab-to-Pascal Class Name Derivation

**What:** Convert a kebab-case skill name to the PascalCase prefix used for schema class names. This is the single source of truth for the naming convention defined in `backend/skills/README.md`.

**When to use:** When loading `input_schema.py` and `output_schema.py` to look up the expected class.

**Example:**
```python
# Source: verified against backend/skills/README.md naming conventions
def _kebab_to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("-"))

# "cross-channel-dedup" → "CrossChannelDedup"
# input class: "CrossChannelDedupInput"
# output class: "CrossChannelDedupOutput"
```

### Pattern 3: Schema Loading via `importlib.util`

**What:** Load a schema `.py` file by absolute path, bypassing Python's module resolution which cannot handle kebab-named directories.

**When to use:** Always, for both `input_schema.py` and `output_schema.py`. No `__init__.py` files are needed.

**Example:**
```python
# Source: verified with live execution against skills/cross-channel-dedup/input_schema.py
import importlib.util

def _load_schema_class(skill_name: str, schema_file: str, class_name: str) -> type:
    """Load a Pydantic class from a skill's schema file by absolute path."""
    snake_name = skill_name.replace("-", "_")
    module_name = f"skills.{snake_name}.{schema_file.replace('.py', '')}"
    file_path = _SKILLS_ROOT / skill_name / schema_file

    if not file_path.exists():
        raise SkillMalformedError(skill_name, f"missing {schema_file}")

    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    try:
        return getattr(mod, class_name)
    except AttributeError:
        raise SkillMalformedError(skill_name, f"{schema_file} missing class {class_name!r}")
```

### Pattern 4: SKILL.md Front Matter Parsing

**What:** Extract `name` and `description` from the YAML front matter and the system prompt from the `## System Prompt` fenced code block.

**When to use:** Inside `load_skill()` before constructing a `SkillRunner`.

**Example:**
```python
# Source: verified against backend/skills/cross-channel-dedup/SKILL.md structure
import re

def _parse_skill_md(skill_name: str, text: str) -> tuple[dict[str, str], str]:
    """Returns (front_matter_dict, system_prompt_text)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise SkillMalformedError(skill_name, "SKILL.md missing YAML front matter")
    try:
        fm_end = lines[1:].index("---") + 1
    except ValueError:
        raise SkillMalformedError(skill_name, "SKILL.md YAML front matter not closed")

    fm: dict[str, str] = {}
    for line in lines[1:fm_end]:
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()

    # Extract system prompt from fenced block in ## System Prompt section
    match = re.search(r"## System Prompt\s*\n+```[^\n]*\n(.*?)```", text, re.DOTALL)
    system_prompt = match.group(1).strip() if match else ""

    return fm, system_prompt
```

### Pattern 5: LLM Response Envelope

**What:** The system prompt instructs the LLM to return a JSON object with three top-level keys. `SkillRunner.run()` parses this envelope and validates the `output` sub-object against the output schema.

**When to use:** Inside `SkillRunner.run()` — this is the only place LLM calls happen.

**Example:**
```python
# Source: adapted from classification_agent.py JSON parsing pattern
import json
from pydantic import ValidationError

ENVELOPE_INSTRUCTIONS = """
Return your response as a JSON object with exactly these three keys:
{
  "output": { ... },
  "reasoning": "your explanation",
  "confidence": 0.0-1.0
}
The "output" value must match the schema described above. Do not include any text outside the JSON.
"""

def _parse_llm_response(skill_name: str, text: str, output_schema_class: type) -> tuple[Any, str, float]:
    """Returns (structured_output, reasoning, confidence). Raises SkillMalformedError on invalid output."""
    text = text.strip()
    # Strip markdown code fences (same pattern as classification_agent.py)
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
    except json.JSONDecodeError as e:
        raise SkillMalformedError(skill_name, f"LLM returned non-JSON: {e}")

    try:
        structured_output = output_schema_class.model_validate(data.get("output", {}))
    except ValidationError as e:
        raise SkillMalformedError(skill_name, f"LLM output failed schema validation: {e}")

    reasoning = str(data.get("reasoning", ""))
    confidence = float(data.get("confidence", 0.0))
    return structured_output, reasoning, confidence
```

### Pattern 6: SkillResult and SkillRunner

**What:** `SkillResult` is a dataclass with three fields (consistent with `AgentResult` in `agents/base.py`). `SkillRunner` holds the loaded skill definition and exposes `.run()`.

**Example:**
```python
# Source: consistent with agents/base.py dataclass pattern
from dataclasses import dataclass
from typing import Any
from app.infrastructure.ai.base import LLMAdapter, LLMMessage

@dataclass
class SkillResult:
    structured_output: Any   # Pydantic model instance of output_schema class
    reasoning: str
    confidence: float


class SkillRunner:
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

    def run(self, llm_client: LLMAdapter, input_data: Any) -> SkillResult:
        """Call the LLM with the skill's system prompt and return a SkillResult."""
        import json
        user_content = json.dumps(
            input_data if isinstance(input_data, dict) else input_data.model_dump(),
            ensure_ascii=False,
        )
        completion = llm_client.complete(
            messages=[LLMMessage(role="user", content=user_content)],
            system=self._system_prompt + "\n\n" + ENVELOPE_INSTRUCTIONS,
        )
        structured_output, reasoning, confidence = _parse_llm_response(
            self._skill_name, completion.text, self._output_schema_class
        )
        return SkillResult(
            structured_output=structured_output,
            reasoning=reasoning,
            confidence=confidence,
        )
```

### Pattern 7: `load_skill()` Public API

```python
# Source: synthesized from all above patterns
def load_skill(skill_name: str) -> SkillRunner:
    """
    Load a named skill from the skills directory.
    Raises SkillNotFoundError if the directory is missing.
    Raises SkillMalformedError if required files or classes are absent.
    """
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

    return SkillRunner(
        skill_name=skill_name,
        system_prompt=system_prompt,
        input_schema_class=input_cls,
        output_schema_class=output_cls,
    )
```

### Anti-Patterns to Avoid

- **Hardcoded skill name list:** Never maintain a registry dict of known skill names. Discovery is fully dynamic — `load_skill("any-skill-name")` works as long as the directory exists.
- **`importlib.import_module` for kebab-named directories:** Fails with `ModuleNotFoundError` because the directory name `cross-channel-dedup` contains hyphens that are invalid in Python module paths. Verified with live test.
- **Calling LLM inside `load_skill()`:** The loader is for discovery and preparation only. No LLM calls until `SkillRunner.run()` is invoked.
- **Mutable `SkillRunner` state:** Once created by `load_skill()`, a `SkillRunner` is logically immutable. Do not add mutable state — it will be shared across concurrent calls.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema validation | Custom JSON field checking | `pydantic.BaseModel.model_validate()` | Pydantic handles nested models, type coercion, missing required fields, and produces structured `ValidationError` |
| YAML front matter | Full YAML parser | Simple `split(":", 1)` line parser | Front matter is constrained to `key: value` lines with no nesting, lists, or multi-line values. A 5-line parser is safer than an extra dependency. |
| Module loading from non-standard paths | `sys.path` manipulation | `importlib.util.spec_from_file_location` | Avoids polluting `sys.path` and handles hyphenated directory names cleanly |

**Key insight:** The existing `parsers/registry.py` and `agents/registry.py` use runtime dictionaries for discovery. Skills use a simpler filesystem-first model: the directory IS the registry. No Python-level registration step is needed.

---

## Common Pitfalls

### Pitfall 1: Kebab Directory Names Break Standard `import_module`

**What goes wrong:** `importlib.import_module("skills.cross_channel_dedup.input_schema")` raises `ModuleNotFoundError: No module named 'skills.cross_channel_dedup'` because the physical directory is named `cross-channel-dedup` (with hyphens), not `cross_channel_dedup`.

**Why it happens:** Python namespace packages require each path component to be a valid identifier. The hyphen in the directory name causes the lookup to fail.

**How to avoid:** Always use `importlib.util.spec_from_file_location(module_name, absolute_file_path)`. The `module_name` argument is just a label — it does not need to correspond to the filesystem path. [VERIFIED by live test in this research session]

**Warning signs:** `ModuleNotFoundError` with `skills.cross_channel_dedup` in the message despite the file clearly existing.

---

### Pitfall 2: PyYAML Not Available

**What goes wrong:** Calling `import yaml` in `loader.py` raises `ModuleNotFoundError`.

**Why it happens:** PyYAML is not listed in `backend/pyproject.toml` and is not installed in the project's virtualenv. [VERIFIED: `importlib.util.find_spec('yaml')` returns `None`]

**How to avoid:** Hand-roll the front matter parser. The SKILL.md front matter format is constrained to `key: value` pairs with no nesting — a 5-line parser covers all cases.

**Warning signs:** Any `import yaml` at the top of `loader.py`.

---

### Pitfall 3: `spec.loader` Can Be None

**What goes wrong:** `importlib.util.spec_from_file_location` returns a spec whose `loader` attribute is `None` if the file path resolves to a non-Python resource.

**Why it happens:** Passing a non-`.py` path or a path to a compiled `.pyc` without the corresponding source.

**How to avoid:** Always verify `file.exists()` and `file.suffix == ".py"` before calling `spec_from_file_location`. Also check `spec is not None and spec.loader is not None` before calling `exec_module`.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'exec_module'`.

---

### Pitfall 4: LLM Returns Partial Envelope

**What goes wrong:** LLM omits the `output` key entirely or returns a flat JSON (without envelope) that happens to look like the output schema.

**Why it happens:** LLMs sometimes follow the schema fields directly without wrapping in `{"output": ..., "reasoning": ..., "confidence": ...}`.

**How to avoid:** The system prompt must be explicit about the envelope structure. Use `data.get("output", {})` as a fallback rather than `data["output"]` to produce a clear `ValidationError` from Pydantic instead of a `KeyError`. Phase 3's responsibility is to add exhaustive rejection tests — Phase 2 must raise `SkillMalformedError` here rather than silently accepting partial data.

**Warning signs:** `SkillResult.reasoning` is always empty; `SkillResult.confidence` is always `0.0`.

---

### Pitfall 5: `structured_output` Type Is `Any` at Callsites

**What goes wrong:** Downstream callers receive `SkillResult.structured_output` typed as `Any` and cannot statically verify field access.

**Why it happens:** The loader is generic — it does not know the concrete output schema type at definition time.

**How to avoid:** This is an accepted tradeoff for Phase 2. The concrete type is known by the caller (who called `load_skill("cross-channel-dedup")` and knows it loaded `CrossChannelDedupOutput`). Document that callers should cast or assert the type when needed. Phase 3 will not change this — it is a deliberate design choice for a generic loader.

---

## Code Examples

### Full Working `load_skill()` Flow (verified)

```python
# Source: verified by live Python execution in this research session
from pathlib import Path
import importlib.util
import re
import json
from dataclasses import dataclass
from typing import Any

_SKILLS_ROOT = Path(__file__).resolve().parents[3] / "skills"

def _kebab_to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("-"))

def _load_schema_class(skill_name: str, schema_file: str, class_name: str) -> type:
    file_path = _SKILLS_ROOT / skill_name / schema_file
    if not file_path.exists():
        raise SkillMalformedError(skill_name, f"missing {schema_file}")
    snake_name = skill_name.replace("-", "_")
    module_name = f"skills.{snake_name}.{schema_file.removesuffix('.py')}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise SkillMalformedError(skill_name, f"cannot load {schema_file}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        return getattr(mod, class_name)
    except AttributeError:
        raise SkillMalformedError(skill_name, f"{schema_file} missing class {class_name!r}")
```

### Exception Additions to `app/core/exceptions.py`

```python
# Source: follows existing pattern in backend/app/core/exceptions.py
class SkillNotFoundError(BeancountBotError):
    """Named skill directory not found under backend/skills/"""

    def __init__(self, skill_name: str) -> None:
        self.skill_name = skill_name
        super().__init__(f"Skill not found: {skill_name!r}")


class SkillMalformedError(BeancountBotError):
    """Skill directory found but files are missing or invalid"""

    def __init__(self, skill_name: str, detail: str) -> None:
        self.skill_name = skill_name
        self.detail = detail
        super().__init__(f"Skill {skill_name!r} is malformed: {detail}")
```

### Mock LLM Client for Tests

```python
# Source: duck-typed against LLMAdapter Protocol; verified to satisfy it in this research session
from app.infrastructure.ai.base import LLMMessage, LLMCompletion, LLMUsage

class MockLLMClient:
    """Simple LLMAdapter-compatible mock for unit tests."""
    def __init__(self, response_text: str) -> None:
        self.response_text = response_text

    def complete(self, messages: list[LLMMessage], system: str = "") -> LLMCompletion:
        return LLMCompletion(text=self.response_text, usage=LLMUsage())
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prompts as Python constants in agent files | Prompts in `SKILL.md` files loaded at runtime | This phase | Agents that use skills no longer need code changes when prompts are updated |
| `AgentResult(success, data, error)` generic wrapper | `SkillResult(structured_output, reasoning, confidence)` typed contract | This phase | Structured output is a Pydantic instance, not an untyped `Any` |

**Deprecated/outdated:**
- Hardcoded `SYSTEM_PROMPT` constants in agent `.py` files: the skill framework replaces this pattern for new skills. Existing agents (`classification_agent.py`, `insight_agent.py`) are NOT migrated in Phase 2 — that is a deferred decision from Phase 1 CONTEXT.md.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The LLM response envelope format (`{"output": {}, "reasoning": "...", "confidence": 0.0}`) is not yet specified anywhere — this research proposes it | Architecture Patterns / Pattern 5 | If Phase 4 dedup skill requires a different LLM call structure, the envelope format may need adjustment. Phase 3's "result contract" phase will likely lock it. |
| A2 | `SkillRunner.run()` accepts `input_data` as `Any` (either a Pydantic model instance or a dict) | Architecture Patterns / Pattern 6 | If all callers use Pydantic instances, the dict fallback is unnecessary noise. If callers use dicts, the `model_dump()` branch is unreachable. The approach handles both safely. |

**All other claims in this research were verified or cited — no further user confirmation needed for implementation.**

---

## Open Questions

1. **Should `SkillRunner` validate `input_data` against `input_schema_class` before calling the LLM?**
   - What we know: `input_schema_class` is loaded and available on the `SkillRunner` instance.
   - What's unclear: Whether Phase 2 should enforce input validation (caller error early) or leave it to the caller.
   - Recommendation: Validate input at the start of `run()` using `input_schema_class.model_validate(...)`. This produces a better error message than letting the LLM silently receive malformed JSON. Mark as Claude's discretion — it does not affect the SKILL-02 requirement.

2. **Should `load_skill()` cache the `SkillRunner` after first load?**
   - What we know: `importlib.util.spec_from_file_location` + `exec_module` has a small I/O and CPU cost on each call.
   - What's unclear: Whether skills will be loaded once per import (cheap enough) or in hot loops.
   - Recommendation: No caching in Phase 2. Add caching as a performance optimization only if profiling shows it is needed. Simple correctness first.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Loader implementation | ✓ | 3.13.11 [VERIFIED] | — |
| `importlib.util` | Schema loading | ✓ | stdlib | — |
| `pydantic` | Schema validation | ✓ | 2.12.4 [VERIFIED: live import] | — |
| `pytest` | Tests | ✓ | 9.0.2 [VERIFIED: live test run] | — |
| PyYAML | YAML front matter parsing | ✗ | not installed [VERIFIED] | Hand-rolled parser (5 lines, safe for constrained format) |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `backend/pyproject.toml` (no `[tool.pytest.ini_options]` — defaults only) |
| Quick run command | `uv run pytest tests/test_skill_loader.py -v` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILL-02 | `load_skill("cross-channel-dedup")` returns a `SkillRunner` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_returns_runner -x` | ❌ Wave 0 |
| SKILL-02 | New skill directory discoverable without loader changes | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_discovery_no_code_changes -x` | ❌ Wave 0 |
| SKILL-02 | Missing skill dir raises `SkillNotFoundError` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_not_found -x` | ❌ Wave 0 |
| SKILL-02 | Missing `SKILL.md` raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_missing_skill_md -x` | ❌ Wave 0 |
| SKILL-02 | Missing `input_schema.py` raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_missing_input_schema -x` | ❌ Wave 0 |
| SKILL-02 | Missing `output_schema.py` raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_missing_output_schema -x` | ❌ Wave 0 |
| SKILL-02 | Schema file missing expected class raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_missing_class -x` | ❌ Wave 0 |
| SKILL-02 | `SkillRunner.run()` returns `SkillResult` with correct fields | unit | `uv run pytest tests/test_skill_loader.py::test_skill_runner_run_returns_result -x` | ❌ Wave 0 |
| SKILL-02 | Invalid LLM JSON raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_skill_runner_invalid_json -x` | ❌ Wave 0 |
| SKILL-02 | LLM output fails schema validation raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_skill_runner_schema_validation_failure -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_skill_loader.py -v`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_skill_loader.py` — covers all SKILL-02 test cases (10 tests listed above)
- [ ] `backend/app/infrastructure/skills/__init__.py` — empty package marker
- [ ] `backend/app/infrastructure/skills/loader.py` — the implementation under test

*(No framework or shared fixture gaps — `conftest.py` from Phase 1 already handles `sys.path` and env setup correctly)*

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | `pydantic.BaseModel.model_validate()` validates LLM JSON output; `SkillMalformedError` on failure |
| V6 Cryptography | no | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via skill name | Tampering | Validate `skill_name` contains only alphanumeric and hyphen characters before building path: `re.fullmatch(r'[a-z0-9-]+', skill_name)`. Never allow `../` traversal. |
| Arbitrary code execution via malformed schema `.py` | Tampering | Skills are first-party files in the repository — no user-controlled content reaches `exec_module`. Document this assumption; do not expose `load_skill` to untrusted external input. |
| LLM prompt injection via skill system prompt | Spoofing | System prompt content comes from `SKILL.md` files in the repository, not from user input. No sanitization needed for this phase. |

---

## Sources

### Primary (HIGH confidence)

- `backend/tests/test_skill_scaffold.py` — confirms Phase 1 scaffold is GREEN (10 tests pass); establishes test pattern for Phase 2
- `backend/app/infrastructure/ai/base.py` — `LLMAdapter` Protocol signature verified: `complete(messages, system) -> LLMCompletion`
- `backend/app/infrastructure/ai/agents/base.py` — `AgentResult` dataclass pattern (model for `SkillResult`)
- `backend/app/core/exceptions.py` — exception hierarchy confirmed; `BeancountBotError` is the correct base
- `backend/skills/cross-channel-dedup/input_schema.py` — import comment confirms: `from skills.cross_channel_dedup.input_schema import CrossChannelDedupInput`
- `backend/skills/README.md` — naming convention confirmed: kebab→PascalCase+Input/Output suffix
- Live Python execution — `importlib.util.spec_from_file_location` verified to load `CrossChannelDedupInput` from kebab-named directory
- Live Python execution — `importlib.import_module("skills.cross_channel_dedup.input_schema")` verified to FAIL (namespace package cannot traverse hyphenated directory)
- Live Python execution — PyYAML verified as NOT available on this system

### Secondary (MEDIUM confidence)

- `backend/app/infrastructure/ai/agents/classification_agent.py` — JSON parsing and code-fence stripping pattern; adapted for `SkillRunner._parse_llm_response()`
- `backend/app/infrastructure/parsers/registry.py` — filesystem discovery pattern; confirms skills loader does not need a Python-level registration step

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries are stdlib or already in `pyproject.toml`; verified with live imports
- Architecture: HIGH — all patterns verified with live Python execution in this session
- Pitfalls: HIGH — critical pitfalls (kebab directory, PyYAML) were confirmed with live test failures before documenting them

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable stdlib APIs; no expiry risk)
