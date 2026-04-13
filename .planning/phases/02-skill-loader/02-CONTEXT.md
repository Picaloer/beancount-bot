# Phase 2: Skill Loader - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `load_skill()` — a dynamic filesystem-based discovery mechanism that, given a
skill name (kebab-case string), returns a `SkillRunner` object ready for invocation. No
LLM is called inside the loader itself. No per-skill code branches in the loader.

Phase 2 delivers:
1. `load_skill("cross-channel-dedup")` discovers and loads the skill from `backend/skills/`
2. A `SkillRunner` class with a `.run(llm_client, input_data)` method
3. `SkillRunner.run()` returns a `SkillResult(structured_output, reasoning, confidence)` — the full result contract is implemented here, not deferred
4. Adding a new skill directory requires no loader code changes
5. Missing/malformed skills fail with a clear error identifying the skill name and the problem

**NOT in scope for Phase 2:**
- Filling in actual system prompts or schema fields (those are Phase 4 content)
- The pipeline gate that runs the skill during import (Phase 5)
- Any UI changes

</domain>

<decisions>
## Implementation Decisions

### Return Type — SkillRunner
- **D-01:** `load_skill("skill-name")` returns a **`SkillRunner`** instance — not a passive
  `SkillDefinition` dataclass and not a plain dict.
- **D-02:** `SkillRunner.run(llm_client, input_data)` accepts an LLM client and the input
  data, calls the LLM, and returns a **`SkillResult`**. Caller injects the LLM client
  (dependency injection — consistent with existing `AIAgent(ABC)` pattern).
- **D-03:** **`SkillResult`** contains exactly three fields:
  - `structured_output` — a validated **Pydantic instance** of the skill's declared `output_schema` class (type-safe, matches the skill's contract)
  - `reasoning` — `str`, the LLM's explanation of its decision
  - `confidence` — numeric, the LLM's stated confidence
- **D-04:** **Phase 2 implements the full `SkillResult` contract.** Phase 3 ("Skill Result
  Contract") will validate and test that the contract is universally applied and that
  malformed LLM outputs are rejected — it is the gatekeeper, not the initial implementor.

### Claude's Discretion
- Loader module location (recommended: `app/infrastructure/skills/loader.py` — a new
  `skills/` sub-package within infrastructure, parallel to `ai/`, `parsers/`, `persistence/`)
- SKILL.md parsing depth (recommended: extract front matter `name`/`description` + raw
  `## System Prompt` fenced block; leave other sections as markdown body)
- Error exception types (recommended: add `SkillNotFoundError` and `SkillMalformedError`
  to `app/core/exceptions.py`, following the existing custom-exception pattern)
- Python import mechanism for schema classes (recommended: `importlib.import_module` with
  kebab→snake_case conversion, matching the comment in `input_schema.py`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — SKILL-02 requirement (Chinese text, authoritative)
- `.planning/ROADMAP.md` — Phase 2 success criteria (4 items); Phase 3 context (result
  contract it must validate); Phase 4 context (will fill prompts/schemas the loader reads)

### Phase 1 Context (locked decisions carried forward)
- `.planning/phases/01-skill-directory-scaffold/01-CONTEXT.md` — all Phase 1 decisions
  are pre-answered (Pydantic schemas, SKILL.md format, kebab-case naming, file structure)

### Codebase Conventions
- `.planning/codebase/STRUCTURE.md` — backend directory layout and layer boundaries
- `.planning/codebase/CONVENTIONS.md` — naming patterns, import organization

### Existing Skill Skeleton (the loader must work against this)
- `backend/skills/cross-channel-dedup/SKILL.md` — YAML front matter format to parse
- `backend/skills/cross-channel-dedup/input_schema.py` — shows expected import path comment:
  `from skills.cross_channel_dedup.input_schema import CrossChannelDedupInput`
- `backend/skills/cross-channel-dedup/output_schema.py` — output schema skeleton
- `backend/skills/README.md` — authoritative naming and structure conventions

### Existing AI Infrastructure (patterns to follow)
- `backend/app/infrastructure/ai/agents/base.py` — `AIAgent(ABC)`, `AgentResult` patterns
- `backend/app/infrastructure/ai/agents/registry.py` — agent registry pattern
- `backend/app/infrastructure/parsers/registry.py` — filesystem-style discovery pattern
- `backend/app/core/exceptions.py` — custom exception pattern to extend for skill errors

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AgentResult` dataclass in `agents/base.py` — shows how the codebase wraps LLM results;
  `SkillResult` will be a similar dataclass with `structured_output`, `reasoning`, `confidence`
- `AIAgent(ABC).run(**kwargs)` in `agents/base.py` — existing agent invocation contract;
  `SkillRunner.run(llm_client, input_data)` is a concrete variant of this pattern
- `factory.py` — `create_llm_client()` caller code can use to get an LLM client to pass in

### Established Patterns
- **Pydantic everywhere**: `output_schema.py` Pydantic class is the natural type for
  `structured_output`; validates LLM JSON output at instantiation time
- **Registry pattern**: `parsers/registry.py` and `agents/registry.py` show how dynamic
  discovery works in this codebase; skills loader follows the same shape
- **Custom exceptions**: `app/core/exceptions.py` defines `UnsupportedFormatError`,
  `ParseError`, `ImportNotFoundError` — skill errors extend this list

### Integration Points
- `backend/skills/` is the root discovery directory (outside `app/` package boundary)
- Schema import path format confirmed in `input_schema.py` comments:
  `from skills.cross_channel_dedup.input_schema import CrossChannelDedupInput`
  → `backend/` must be on `sys.path` and `skills/` must be a Python package (add `__init__.py` if missing)
- `app/infrastructure/ai/factory.py` — downstream callers use this to create the LLM
  client they inject into `SkillRunner.run()`

</code_context>

<specifics>
## Specific Ideas

- `SkillRunner.run()` should validate the raw LLM JSON output against the output_schema
  Pydantic class before returning `structured_output` — invalid output should raise a
  `SkillMalformedError` (Phase 3 will add more exhaustive rejection tests on top of this)
- The kebab→snake_case conversion should be the single source of truth for the naming
  convention: `"cross-channel-dedup"` → `"cross_channel_dedup"` → `CrossChannelDedupInput`

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-skill-loader*
*Context gathered: 2026-04-13*
