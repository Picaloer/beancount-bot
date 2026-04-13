# Phase 1: Skill Directory Scaffold - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish the on-disk structure and file format conventions for `backend/skills/`. No Python loader code is written in this phase — that is Phase 2's responsibility. Phase 1 delivers:

1. `backend/skills/` directory at the top level of the backend (alongside `app/`, `tests/`, etc.)
2. A file-format convention for every skill directory: `SKILL.md` + `input_schema.py` + `output_schema.py`
3. One concrete skill skeleton: `cross-channel-dedup/` with all required files present (content is TBD placeholders)

**NOT in scope for Phase 1:**
- Any `load_skill()` Python function or loader logic (Phase 2)
- Migrating existing `classification_agent.py` / `insight_agent.py` prompts into skills/ (deferred)
- Creating `internal-transfer-detection/` skill directory (Phase 7+)

</domain>

<decisions>
## Implementation Decisions

### Schema File Format
- **D-01:** Schema files use **Pydantic models** (`.py` files) — consistent with the existing codebase which uses Pydantic extensively for request/response models and settings.
- **D-02:** Each skill directory has **two separate schema files**: `input_schema.py` and `output_schema.py`. The split keeps input and output contracts independently readable and allows them to grow in complexity without conflating concerns.

### Skill Directory Scope
- **D-03:** Phase 1 creates **only one skill directory**: `cross-channel-dedup/`. Creating `internal-transfer-detection/` before its requirements are concrete would risk premature schema definitions.
- **D-04:** The `cross-channel-dedup/` directory is a **skeleton** — all required files (`SKILL.md`, `input_schema.py`, `output_schema.py`) are present with correct structure, but prompt text and schema field details use `# TODO` / `# TBD` placeholders. Actual content is written in Phase 4.

### SKILL.md Content Structure
- **D-05:** `SKILL.md` uses a **full documentation format** with these sections (all present in Phase 1, content TBD where noted):
  1. Metadata header (YAML front matter): `name` and `description` — minimal set, no `version` or `model_hint` in the header
  2. `## Purpose` — brief description of what the skill does and when it is used
  3. `## System Prompt` — the skill's LLM system prompt (TBD in Phase 1)
  4. `## Input` — description of what the caller passes in, referencing `input_schema.py`
  5. `## Output` — description of what the skill returns, referencing `output_schema.py`
  6. `## Usage Example` — a code/data example showing a real call (TBD placeholder in Phase 1)

### Existing Code
- **D-06:** Phase 1 does **not** touch `classification_agent.py`, `insight_agent.py`, or any existing Python code. The scaffold is purely additive.

### Claude's Discretion
- Whether to add a top-level `backend/skills/README.md` explaining the conventions (recommended: yes, to satisfy SC-3 verifiability)
- The exact Pydantic base classes and field naming in the skeleton schemas (`BaseModel` subclass with appropriate field stubs)
- Whether `SKILL.md` uses a fenced code block or a tagged section for the prompt

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — SKILL-01 requirement definition (Chinese text, authoritative)
- `.planning/ROADMAP.md` — Phase 1 success criteria (4 items); Phase 2 and 4 context for what the loader and dedup skill will expect

### Codebase Conventions
- `.planning/codebase/STRUCTURE.md` — backend directory layout; confirms `backend/` top-level structure, shows where `app/`, `tests/` live
- `.planning/codebase/CONVENTIONS.md` — naming patterns, import organization, data modeling (Pydantic/dataclass usage)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/infrastructure/ai/agents/base.py` — `AgentResult` dataclass pattern; shows how the codebase wraps LLM call results
- `backend/app/infrastructure/parsers/base.py` — `BillParserAdapter(ABC)` shows how existing "plugin" contracts are defined
- `backend/app/infrastructure/parsers/registry.py` — parser self-registration pattern; skills will use a similar discovery approach in Phase 2

### Established Patterns
- **Pydantic everywhere**: `pydantic-settings` for config, request/response models in API layer — `input_schema.py` / `output_schema.py` as `BaseModel` subclasses is consistent
- **Prompts as Python constants**: `SYSTEM_PROMPT` in `classification_agent.py` (line 19) is the current pattern the skill framework is replacing
- **ABC base classes**: `BillParserAdapter(ABC)`, `ClassificationStage(ABC)`, `AIAgent(ABC)` — skill contracts may follow this pattern in Phase 2

### Integration Points
- `backend/app/infrastructure/ai/agents/` — existing agents that will eventually be refactored to load prompts from skills/
- `backend/app/infrastructure/parsers/__init__.py` — self-registration via import; Phase 2's loader will use a filesystem discovery approach instead

</code_context>

<specifics>
## Specific Ideas

- The `cross-channel-dedup/` skeleton should demonstrate the full convention clearly enough that a developer reading it can replicate the structure for a new skill without additional guidance.
- The top-level `backend/skills/README.md` (if created) should explain: directory naming (kebab-case), required files, and how to add a new skill — this directly satisfies Success Criteria 3.

</specifics>

<deferred>
## Deferred Ideas

- **Existing prompt migration**: Moving `classification_agent.py:SYSTEM_PROMPT` and `insight_agent.py` prompt text into `backend/skills/` directories was explicitly deferred. Phase 1 does not touch existing agent code. (User decision — not a scope addition for this phase.)
- **`internal-transfer-detection/` skill directory**: Will be created in or before Phase 7 when requirements are concrete.
- **`model_hint` / `version` in SKILL.md metadata**: Kept out of the minimal metadata set. Can be added to the schema later if Phase 2's loader needs it.

</deferred>

---

*Phase: 01-skill-directory-scaffold*
*Context gathered: 2026-04-13*
