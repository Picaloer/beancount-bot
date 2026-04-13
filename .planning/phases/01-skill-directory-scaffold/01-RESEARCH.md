# Phase 1: Skill Directory Scaffold - Research

**Researched:** 2026-04-13
**Domain:** Python directory conventions, Pydantic v2 schema contracts, Markdown YAML front matter
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Schema files use **Pydantic models** (`.py` files) — consistent with the existing codebase which uses Pydantic extensively for request/response models and settings.
- **D-02:** Each skill directory has **two separate schema files**: `input_schema.py` and `output_schema.py`. The split keeps input and output contracts independently readable and allows them to grow in complexity without conflating concerns.
- **D-03:** Phase 1 creates **only one skill directory**: `cross-channel-dedup/`. Creating `internal-transfer-detection/` before its requirements are concrete would risk premature schema definitions.
- **D-04:** The `cross-channel-dedup/` directory is a **skeleton** — all required files (`SKILL.md`, `input_schema.py`, `output_schema.py`) are present with correct structure, but prompt text and schema field details use `# TODO` / `# TBD` placeholders. Actual content is written in Phase 4.
- **D-05:** `SKILL.md` uses a **full documentation format** with these sections (all present in Phase 1, content TBD where noted):
  1. Metadata header (YAML front matter): `name` and `description` — minimal set, no `version` or `model_hint` in the header
  2. `## Purpose` — brief description of what the skill does and when it is used
  3. `## System Prompt` — the skill's LLM system prompt (TBD in Phase 1)
  4. `## Input` — description of what the caller passes in, referencing `input_schema.py`
  5. `## Output` — description of what the skill returns, referencing `output_schema.py`
  6. `## Usage Example` — a code/data example showing a real call (TBD placeholder in Phase 1)
- **D-06:** Phase 1 does **not** touch `classification_agent.py`, `insight_agent.py`, or any existing Python code. The scaffold is purely additive.

### Claude's Discretion

- Whether to add a top-level `backend/skills/README.md` explaining the conventions (recommended: yes, to satisfy SC-3 verifiability)
- The exact Pydantic base classes and field naming in the skeleton schemas (`BaseModel` subclass with appropriate field stubs)
- Whether `SKILL.md` uses a fenced code block or a tagged section for the prompt

### Deferred Ideas (OUT OF SCOPE)

- **Existing prompt migration**: Moving `classification_agent.py:SYSTEM_PROMPT` and `insight_agent.py` prompt text into `backend/skills/` directories. Phase 1 does not touch existing agent code.
- **`internal-transfer-detection/` skill directory**: Will be created in or before Phase 7 when requirements are concrete.
- **`model_hint` / `version` in SKILL.md metadata**: Kept out of the minimal metadata set. Can be added to the schema later if Phase 2's loader needs it.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKILL-01 | 建立 `backend/skills/` 目录，每个 skill 以独立子目录形式存放，包含 `SKILL.md`（定义 skill 的 prompt、输入/输出 schema）和必要的 schema 文件 | Directory layout conventions, Pydantic BaseModel pattern for schema files, YAML front matter convention for SKILL.md |
</phase_requirements>

---

## Summary

Phase 1 is a pure additive file-and-directory creation task: no existing Python code is modified. The deliverable is `backend/skills/cross-channel-dedup/` with three files (`SKILL.md`, `input_schema.py`, `output_schema.py`) and an optional top-level `backend/skills/README.md`.

The primary design questions are (1) what exact Pydantic pattern to use in the schema files so Phase 2's loader can import them cleanly, and (2) what YAML front-matter format to use in `SKILL.md` so the loader can parse metadata without a full Markdown library. Both questions have clear answers from the codebase and official docs.

The main planning risk is over-specifying schema field names for `cross-channel-dedup/` in Phase 1, when Phase 4 will actually design the skill. The right posture is: correct module skeleton (importable `BaseModel` subclass), placeholder fields, and `# TODO` comments. No runtime or test infrastructure needs to change for this phase.

**Primary recommendation:** Create three concrete files in `backend/skills/cross-channel-dedup/` with the minimum viable structure that Phase 2 can import and Phase 4 can fill in — plus a `README.md` at `backend/skills/` that documents the naming and file conventions so Success Criteria 3 is verifiable without running any code.

---

## Project Constraints (from CLAUDE.md)

| Directive | Source | Impact on Phase |
|-----------|--------|-----------------|
| New feature work must branch off `master`, merged back after regression testing | CLAUDE.md rule 1 | Plan must include branch step |
| Tech stack: Python 3.13 / FastAPI / SQLAlchemy / PostgreSQL / Celery + Redis — **no new runtimes** | CLAUDE.md constraints | No new dependencies needed for directory scaffold |
| Package manager for backend: `uv`, run commands as `uv run <cmd>` | CLAUDE.md tech stack | Test commands use `uv run pytest` |
| No CI/CD pipeline configured | CLAUDE.md gaps | No automated gate; manual verification only |
| No Python linter/formatter config enforced in repo | CLAUDE.md gaps | Code style follows developer convention; no linting step needed in plan |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.12.5 | Input/output schema definitions as `BaseModel` subclasses | Already the codebase standard for all request/response contracts; installed in backend venv [VERIFIED: pypi.org, backend venv] |
| Python stdlib `pathlib` | built-in (3.13) | Future loader uses `Path` for filesystem traversal | Used throughout codebase for file operations [VERIFIED: codebase grep] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.3 (latest) / 9.0.2 (installed) | Verification tests for directory structure | Used in backend for all existing tests [VERIFIED: pypi.org, uv lock] |

**No new package dependencies are required for Phase 1.** All tooling is already installed.

**Version verification:**
```bash
cd backend && uv run python -c "import pydantic; print(pydantic.__version__)"
# confirmed: 2.12.5
cd backend && uv run pytest --version
# confirmed: pytest 9.0.2
```
[VERIFIED: actual command execution in this session]

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── skills/                         # NEW — skill plugin directory
│   ├── README.md                   # Convention documentation (optional, recommended)
│   └── cross-channel-dedup/        # Skill subdirectory (kebab-case naming)
│       ├── SKILL.md                # Skill documentation + YAML front matter
│       ├── input_schema.py         # Pydantic BaseModel subclass for input
│       └── output_schema.py        # Pydantic BaseModel subclass for output
├── app/                            # UNCHANGED
│   └── infrastructure/ai/agents/  # Existing agents — not touched in Phase 1
└── tests/
    └── test_skill_scaffold.py      # Structural assertions (no runtime needed)
```

The `backend/skills/` directory sits alongside `backend/app/` at the top level of the backend package — consistent with how `backend/alembic/` and `backend/tests/` are peers to `backend/app/`. [VERIFIED: STRUCTURE.md confirms backend layout]

### Pattern 1: Pydantic BaseModel as Schema Contract

**What:** Each schema file exports a single `BaseModel` subclass representing the data shape.

**When to use:** Any time you need the loader (Phase 2) to import the schema without executing LLM code.

**Example — input_schema.py skeleton:**
```python
# Source: official Pydantic v2 docs (pydantic.dev) + existing codebase patterns
"""
Input schema for the cross-channel-dedup skill.
"""
from pydantic import BaseModel

# TODO (Phase 4): Define fields once the dedup skill design is complete.
class CrossChannelDedupInput(BaseModel):
    pass  # placeholder
```

**Example — output_schema.py skeleton:**
```python
"""
Output schema for the cross-channel-dedup skill.
"""
from pydantic import BaseModel

# TODO (Phase 4): Define fields once the dedup skill design is complete.
class CrossChannelDedupOutput(BaseModel):
    pass  # placeholder
```

**Why Pydantic BaseModel specifically:**
- `BaseModel.model_validate(data)` validates any dict-based input automatically [VERIFIED: pydantic.dev docs]
- `BaseModel.model_json_schema()` generates a JSON Schema 2020-12 / OpenAPI 3.1 compatible schema dict — Phase 2's loader can use this for contract introspection without parsing `.py` source [VERIFIED: pydantic.dev docs]
- Consistent with every API request/response model in the existing codebase (`RuleCreate`, `CategoryUpdate`, `RuleSuggestionCreate`, etc.) [VERIFIED: codebase grep]

### Pattern 2: Class Naming Convention for Schema Files

**What:** Class name = PascalCase of the skill directory name + `Input` / `Output` suffix.

| Skill directory | InputSchema class | OutputSchema class |
|-----------------|-------------------|--------------------|
| `cross-channel-dedup/` | `CrossChannelDedupInput` | `CrossChannelDedupOutput` |
| `internal-transfer-detection/` | `InternalTransferDetectionInput` | `InternalTransferDetectionOutput` |

This mirrors the existing `ORM`-suffix pattern for SQLAlchemy models and makes the Phase 2 loader's import target predictable: `from skills.cross_channel_dedup.input_schema import CrossChannelDedupInput`. [ASSUMED — loader will use directory-name-to-module-name translation; confirmed by parser registry analogy in codebase]

**Directory name to module name translation:** kebab-case directory names (`cross-channel-dedup`) become snake\_case module paths (`cross_channel_dedup`). Python does not allow hyphens in import paths, so the loader must translate at load time. Phase 2 handles this — Phase 1 only needs to use the kebab-case directory naming.

### Pattern 3: YAML Front Matter in SKILL.md

**What:** A YAML block delimited by `---` lines, placed first in the file.

**When to use:** All `SKILL.md` files. The block must be the first content in the file. [VERIFIED: Jekyll YAML front-matter spec, confirmed by general convention]

**Example:**
```markdown
---
name: cross-channel-dedup
description: Identify suspected duplicate transactions across multiple payment channels (WeChat, Alipay, bank cards) using LLM semantic comparison.
---

## Purpose
...
```

**Why the `---` delimiter is the right choice:**
- Universal YAML front-matter convention (Jekyll, Hugo, Obsidian, many static site generators)
- Trivially parseable by Python `yaml.safe_load()` without a Markdown library
- No ambiguity about where the metadata block ends
- Consistent with how existing `CLAUDE.md` and planning markdown files use explicit section delimiters

### Pattern 4: Skill Directory Naming

**What:** kebab-case, all lowercase, hyphen-separated. [ASSUMED — based on the one named example in CONTEXT.md and consistency with the project's existing `snake_case` Python naming + URL/path conventions]

**Examples:** `cross-channel-dedup/`, `internal-transfer-detection/`

### Existing Plugin Analogy: Parser Registry

The existing parser plugin system is the closest prior art in this codebase:

```
backend/app/infrastructure/parsers/
├── base.py       # BillParserAdapter(ABC) — contract
├── registry.py   # register() + auto_detect_file() — discovery
├── wechat.py     # concrete adapter
├── alipay.py     # concrete adapter
├── cmb.py        # concrete adapter
└── __init__.py   # triggers self-registration on import
```

The skill directory system in Phase 1 provides the **on-disk equivalent of the parser adapters** — `SKILL.md` maps to the adapter's metadata properties (`source_type`, `description`), and the schema files map to the adapter's type contracts (`can_parse`, `parse` return type). Phase 2's loader will provide the filesystem-discovery equivalent of `registry.py`. [VERIFIED: codebase inspection]

### Anti-Patterns to Avoid

- **Importing `app.*` from schema files:** `input_schema.py` and `output_schema.py` must import only from stdlib and `pydantic`. Importing from `app.core` or `app.domain` creates coupling between the skill layer and the application layer — the skill directory is designed to be application-independent.
- **Putting prompt text in `input_schema.py`:** Prompts belong in `SKILL.md`. Schema files are code contracts, not content.
- **snake_case directory names:** Python's import system uses snake\_case for packages, but the skill directories use kebab-case to signal they are content/resource directories, not Python packages. The loader handles the translation. Using snake\_case directories would reduce readability and obscure this distinction.
- **Omitting the `pass` placeholder in empty BaseModel subclasses:** An empty class body without `pass` is a syntax error in Python. Placeholder models need `pass` until Phase 4 adds real fields.
- **Creating an `__init__.py` inside skill directories:** Skill directories are NOT Python packages; they are resource directories. An `__init__.py` would invite direct Python imports that bypass the loader, undermining Phase 2's design.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema validation | Custom dict-checking code | `pydantic.BaseModel` | 50+ edge cases around type coercion, optional fields, nested models; Pydantic handles all of them [VERIFIED: docs] |
| JSON Schema export | Manual schema dict construction | `BaseModel.model_json_schema()` | Standards-compliant output (JSON Schema 2020-12) with zero extra code [VERIFIED: docs] |
| YAML front-matter parsing | Custom string-split logic | `yaml.safe_load()` (stdlib `yaml`) | One-liner; handles all valid YAML including multiline strings and special characters [ASSUMED] |

**Key insight:** Phase 1 has no custom logic at all — it is only files. The "don't hand-roll" items are important guidance for Phase 2's loader, which this research anticipates so the planner can note them as constraints for later phases.

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is a greenfield additive phase. No existing code, data, or configuration is renamed or refactored. No runtime state is affected.

---

## Environment Availability Audit

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Schema files (runtime) | yes | 3.13.11 | — |
| uv | Running pytest | yes | 0.9.29 | — |
| pydantic | `input_schema.py`, `output_schema.py` | yes | 2.12.5 | — |
| pytest | Structural verification tests | yes | 9.0.2 | — |
| Git | Branch creation per CLAUDE.md | yes (git repo confirmed) | — | — |

[VERIFIED: command execution — `uv --version`, `uv run python --version`, `uv run python -c "import pydantic; print(pydantic.__version__)"`, `uv run pytest --version`]

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## Common Pitfalls

### Pitfall 1: Module-Import Error When Loader Tries kebab-case Directory

**What goes wrong:** `import cross-channel-dedup` raises `SyntaxError` because Python identifiers cannot contain hyphens.

**Why it happens:** Directory names use kebab-case but Python module system uses snake\_case.

**How to avoid:** Phase 2's loader must translate directory names before importing: `skill_dir.name.replace("-", "_")`. Phase 1 is safe — it only creates files, not import paths.

**Warning signs:** Any test that does `import cross_channel_dedup` in Phase 1 will fail unless the loader wrapper is in place first.

### Pitfall 2: `SKILL.md` Sections Missing — Loader Fails Silently in Phase 2

**What goes wrong:** If `SKILL.md` is missing a required section (e.g., `## System Prompt`), Phase 2's loader may either crash or return an empty string for the prompt, causing the LLM call to use no system instruction.

**Why it happens:** Markdown section parsing is often written with `str.split("## Section Name")` which returns two-element lists only if the section exists.

**How to avoid:** The Phase 1 skeleton must include ALL required sections (even if TBD). The sections are: YAML front matter, `## Purpose`, `## System Prompt`, `## Input`, `## Output`, `## Usage Example`. This is already locked in D-05.

**Warning signs:** Phase 2 loader test sees `""` or `None` for system prompt even though `SKILL.md` exists.

### Pitfall 3: Empty BaseModel Subclass Missing `pass`

**What goes wrong:** `SyntaxError` when loading the schema module.

**Why it happens:** `class CrossChannelDedupInput(BaseModel):` with nothing in the body is invalid Python syntax.

**How to avoid:** Always write `pass` in empty placeholder class bodies.

### Pitfall 4: Schema Files Import from `app.*`

**What goes wrong:** Circular imports or import errors when Phase 2's loader imports schema files in contexts where `app.core` is not initialized (e.g., standalone tests).

**Why it happens:** Convenience — it's easy to accidentally import an existing enum or model.

**How to avoid:** `input_schema.py` and `output_schema.py` must import ONLY from Python stdlib and `pydantic`. No `from app.*` imports. This is validated by running the schema import in a minimal test environment without the full FastAPI app.

### Pitfall 5: Prompt Text in Fenced Code Block vs. Plain Section

**What goes wrong (if fenced):** Phase 2's loader must strip the ` ```  ``` ` delimiters and language tag. If it doesn't, the literal backticks are sent to the LLM.

**What goes wrong (if plain):** Next Markdown `##` section header is accidentally included in the prompt text if the parser splits on `## System Prompt\n` but not on the next `## `.

**How to avoid:** Use a **fenced code block** (` ``` `) inside `## System Prompt` for the prompt text. This is the cleaner convention: it makes the prompt visually distinct in documentation, and the parser only needs to extract content between the first ` ``` ` and the closing ` ``` ` within the section. Document this choice in `backend/skills/README.md`.

---

## Code Examples

Verified patterns from official sources and codebase inspection:

### input_schema.py — Full skeleton pattern
```python
# Source: Pydantic v2 docs (pydantic.dev) + existing codebase BaseModel usage
"""
Input schema for the cross-channel-dedup skill.

Imported by the Phase 2 loader via:
    from skills.cross_channel_dedup.input_schema import CrossChannelDedupInput
"""
from pydantic import BaseModel


class CrossChannelDedupInput(BaseModel):
    # TODO (Phase 4): Add fields once the dedup skill design is complete.
    # Expected fields: existing_transactions (list), new_transactions (list),
    # window_days (int, default 7)
    pass
```

### output_schema.py — Full skeleton pattern
```python
# Source: Pydantic v2 docs (pydantic.dev)
"""
Output schema for the cross-channel-dedup skill.

Imported by the Phase 2 loader via:
    from skills.cross_channel_dedup.output_schema import CrossChannelDedupOutput
"""
from pydantic import BaseModel


class CrossChannelDedupOutput(BaseModel):
    # TODO (Phase 4): Add fields once the dedup skill design is complete.
    # Expected fields: suspected_pairs (list of {tx_a_id, tx_b_id, similarity_score,
    #                  reasoning, suggested_keep}), window_count (int)
    pass
```

### SKILL.md — Full skeleton with YAML front matter
```markdown
---
name: cross-channel-dedup
description: Identify suspected duplicate transactions across multiple payment channels using LLM semantic comparison grouped by weekly time windows.
---

## Purpose

Cross-channel deduplication detects cases where the same underlying payment appears in
multiple bill exports — for example, a WeChat Pay deduction that also shows up as a CMB
bank card charge. The skill compares already-imported transactions against newly uploaded
transactions, grouped into 7-day sliding windows, and returns suspected duplicate pairs.

Used by: the import pipeline before classification (Phase 5 gate).

## System Prompt

```
TODO (Phase 4): Add the LLM system prompt here.
```

## Input

Defined in `input_schema.py` — see `CrossChannelDedupInput`.

TODO (Phase 4): Describe the input fields once the schema is finalized.

## Output

Defined in `output_schema.py` — see `CrossChannelDedupOutput`.

TODO (Phase 4): Describe the output fields once the schema is finalized.

## Usage Example

TODO (Phase 4): Add a code snippet showing how to invoke this skill.
```

### backend/skills/README.md — Convention documentation
```markdown
# Skills Directory

Each subdirectory in `backend/skills/` is a **skill** — a self-contained LLM capability
definition that can be loaded and invoked by the skill framework.

## Structure

Every skill directory must contain:

| File | Purpose |
|------|---------|
| `SKILL.md` | Documentation: YAML front matter + sections |
| `input_schema.py` | Pydantic `BaseModel` subclass defining the skill's input |
| `output_schema.py` | Pydantic `BaseModel` subclass defining the skill's output |

## Adding a New Skill

1. Create a new subdirectory under `backend/skills/` using **kebab-case** naming.
2. Create all three required files (`SKILL.md`, `input_schema.py`, `output_schema.py`).
3. Do not modify any existing code — the skill loader discovers skills automatically.

## Naming Conventions

- Directory name: `kebab-case` — e.g., `cross-channel-dedup`
- Schema class names: PascalCase of directory name + `Input`/`Output` suffix
  - `cross-channel-dedup` → `CrossChannelDedupInput`, `CrossChannelDedupOutput`

## SKILL.md Format

```
---
name: <kebab-case-name>
description: <one-sentence description>
---

## Purpose
## System Prompt
## Input
## Output
## Usage Example
```

The `## System Prompt` section contains the LLM system prompt inside a fenced code block.

## Schema File Rules

- Import ONLY from stdlib and `pydantic` — no `from app.*` imports
- Export exactly one class per file named `<SkillName>Input` / `<SkillName>Output`
- Use `pass` as placeholder body until the skill is fully designed
```

### Structural verification test pattern (pytest)
```python
# Source: existing backend test conventions (conftest.py, test file structure)
# backend/tests/test_skill_scaffold.py
"""Verify the skills directory structure meets Phase 1 success criteria."""
from pathlib import Path
import importlib
import sys

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
SKILL_NAME = "cross-channel-dedup"


def test_skills_directory_exists():
    assert SKILLS_DIR.is_dir(), f"backend/skills/ not found at {SKILLS_DIR}"


def test_skill_subdirectory_exists():
    assert (SKILLS_DIR / SKILL_NAME).is_dir()


def test_skill_md_exists():
    assert (SKILLS_DIR / SKILL_NAME / "SKILL.md").is_file()


def test_skill_md_has_yaml_frontmatter():
    text = (SKILLS_DIR / SKILL_NAME / "SKILL.md").read_text()
    lines = text.splitlines()
    assert lines[0].strip() == "---", "SKILL.md must start with YAML front matter delimiter"
    closing = lines[1:].index("---") if "---" in lines[1:] else -1
    assert closing >= 0, "SKILL.md YAML front matter must have a closing ---"


def test_skill_md_has_required_sections():
    text = (SKILLS_DIR / SKILL_NAME / "SKILL.md").read_text()
    for section in ["## Purpose", "## System Prompt", "## Input", "## Output", "## Usage Example"]:
        assert section in text, f"SKILL.md missing section: {section}"


def test_input_schema_exists():
    assert (SKILLS_DIR / SKILL_NAME / "input_schema.py").is_file()


def test_output_schema_exists():
    assert (SKILLS_DIR / SKILL_NAME / "output_schema.py").is_file()


def test_input_schema_importable():
    module_path = SKILLS_DIR / SKILL_NAME.replace("-", "_")
    # The loader translates kebab-case dir to snake_case module path
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "input_schema",
        SKILLS_DIR / SKILL_NAME / "input_schema.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "CrossChannelDedupInput")


def test_output_schema_importable():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "output_schema",
        SKILLS_DIR / SKILL_NAME / "output_schema.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "CrossChannelDedupOutput")


def test_schema_files_no_app_imports():
    for schema_file in ["input_schema.py", "output_schema.py"]:
        text = (SKILLS_DIR / SKILL_NAME / schema_file).read_text()
        assert "from app." not in text, f"{schema_file} must not import from app.*"
        assert "import app." not in text, f"{schema_file} must not import from app.*"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `SYSTEM_PROMPT = """..."""` hardcoded in each agent file | Skill directory with `SKILL.md` + schema files | Phase 1 introduces the new convention | Prompts become editable without touching Python code |
| Prompts embedded in `classification_agent.py`, `insight_agent.py` | Kept in place until Phase 4 migration | Out of scope for Phase 1 | Existing agents are untouched |

**Deprecated/outdated patterns this phase will eventually replace:**

- `SYSTEM_PROMPT` string constants in `backend/app/infrastructure/ai/agents/*.py` — these will be migrated to `backend/skills/` in Phase 4+. Phase 1 does not remove them.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Directory naming convention is kebab-case (e.g., `cross-channel-dedup/`) | Architecture Patterns — Pattern 4 | If Phase 2's loader uses a different convention, directory names must be renamed |
| A2 | The Phase 2 loader will translate `cross-channel-dedup` → `cross_channel_dedup` to form the Python module path | Architecture Patterns — Pattern 2 | If loader uses a different import strategy (e.g., dynamic exec), the naming convention guidance is moot |
| A3 | `yaml.safe_load()` from Python stdlib `yaml` module is available (it is part of `PyYAML` which must be installed separately — it is NOT in the Python standard library) | Don't Hand-Roll | Phase 2 loader will need `PyYAML` installed if it parses YAML front matter; this phase does not need it |

**Note on A3:** `yaml` is commonly assumed to be stdlib but is actually `PyYAML` (third-party). The backend's `pyproject.toml` does not currently list `pyyaml` as a dependency [VERIFIED: pyproject.toml inspection]. Phase 2 will need to add it, or use a regex/string-split approach to extract front matter. This does not affect Phase 1 at all.

---

## Open Questions

1. **Should `backend/skills/README.md` be created in Phase 1 or left to Phase 2?**
   - What we know: CONTEXT.md says "recommended: yes, to satisfy SC-3 verifiability"
   - What's unclear: Whether it counts as Phase 1 scope or implementation detail
   - Recommendation: Include it in Phase 1. Success Criterion 3 ("A developer can add a new skill by creating a new subdirectory without modifying existing feature code") is most verifiable when the conventions are written down in `README.md`. The planner should include one task for this file.

2. **Does `backend/skills/` need an `__init__.py`?**
   - What we know: The directory should NOT be a Python package (to prevent direct `import skills.*` bypassing the loader). The loader will use `importlib.util.spec_from_file_location()` for direct file loading.
   - What's unclear: Whether any CI tool or IDE setup requires `__init__.py` for path resolution
   - Recommendation: Do NOT create `__init__.py`. The skill directories are resource directories, not Python packages.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 (installed in backend venv) |
| Config file | None (no `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml`) |
| Quick run command | `cd backend && uv run pytest tests/test_skill_scaffold.py -v` |
| Full suite command | `cd backend && uv run pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILL-01 | `backend/skills/` exists | unit | `uv run pytest tests/test_skill_scaffold.py::test_skills_directory_exists -x` | No — Wave 0 gap |
| SKILL-01 | `cross-channel-dedup/` subdirectory exists | unit | `uv run pytest tests/test_skill_scaffold.py::test_skill_subdirectory_exists -x` | No — Wave 0 gap |
| SKILL-01 | `SKILL.md` present with YAML front matter | unit | `uv run pytest tests/test_skill_scaffold.py::test_skill_md_has_yaml_frontmatter -x` | No — Wave 0 gap |
| SKILL-01 | `SKILL.md` has all required sections | unit | `uv run pytest tests/test_skill_scaffold.py::test_skill_md_has_required_sections -x` | No — Wave 0 gap |
| SKILL-01 | `input_schema.py` importable, exports correct class | unit | `uv run pytest tests/test_skill_scaffold.py::test_input_schema_importable -x` | No — Wave 0 gap |
| SKILL-01 | `output_schema.py` importable, exports correct class | unit | `uv run pytest tests/test_skill_scaffold.py::test_output_schema_importable -x` | No — Wave 0 gap |
| SKILL-01 | Schema files do not import from `app.*` | unit | `uv run pytest tests/test_skill_scaffold.py::test_schema_files_no_app_imports -x` | No — Wave 0 gap |
| SC-3 | `README.md` exists at `backend/skills/README.md` | manual-verify | `ls backend/skills/README.md` | No — created in phase |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/test_skill_scaffold.py -v`
- **Per wave merge:** `cd backend && uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_skill_scaffold.py` — covers all SKILL-01 structural assertions (test code provided in Code Examples section above)

---

## Security Domain

Phase 1 creates only static files (Markdown, Python schema stubs). There is no user input handling, no API endpoints, no database operations, no credentials, and no LLM calls.

**ASVS Assessment:** Not applicable. No security controls required for directory scaffolding.

---

## Sources

### Primary (HIGH confidence)
- Pydantic v2 official docs (pydantic.dev) — BaseModel usage, model validation methods, `model_json_schema()` confirmed
- PyPI official release page — Pydantic 2.12.5 (latest), pytest 9.0.3 (latest) versions confirmed
- CONTEXT.md — locked design decisions D-01 through D-06
- REQUIREMENTS.md — SKILL-01 requirement definition
- ROADMAP.md — Phase 1 and Phase 2 success criteria
- Codebase inspection — backend directory layout, existing Pydantic usage in API layer, parser registry pattern, `SYSTEM_PROMPT` constant in `classification_agent.py` and `insight_agent.py`, `conftest.py` test patterns

### Secondary (MEDIUM confidence)
- Jekyll YAML front matter documentation — `---` delimiter spec confirmed

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — no new dependencies; all library versions verified against live venv and pypi.org
- Architecture: HIGH — Pydantic pattern verified against official docs and existing codebase; directory layout verified against STRUCTURE.md and actual filesystem; `SYSTEM_PROMPT` location verified by grep
- Pitfalls: HIGH for syntax and import risks (deterministic); MEDIUM for loader-design pitfalls (Phase 2 is not yet planned)
- Test patterns: HIGH — pytest version and invocation verified; test code follows existing conftest.py patterns

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable stack; Pydantic 2.x API is stable; no breaking changes anticipated in this timeframe)
