---
phase: 02-skill-loader
plan: 02
subsystem: skill-loader
tags: [python, importlib, pydantic, tdd, green-phase, skill-loader]

# Dependency graph
requires:
  - phase: 02-skill-loader
    plan: 01
    provides: 11 RED tests, SkillNotFoundError/SkillMalformedError, loader.py stub

provides:
  - load_skill() — dynamic filesystem skill loader
  - SkillRunner — executes skill against any LLMAdapter-compatible client
  - SkillResult — dataclass with structured_output (Pydantic), reasoning (str), confidence (float)
  - _SKILLS_ROOT module-level Path for test isolation via patch.object

affects:
  - Phase 3 (skill result contract) — depends on SkillResult dataclass shape
  - Phase 5 (pipeline gate) — wires load_skill() into import pipeline
  - Any future skill (Phase 4+) — load_skill("new-skill") discovers new directory without loader code changes

# Tech tracking
tech-stack:
  added:
    - importlib.util.spec_from_file_location for loading .py files from kebab-named directories
  patterns:
    - TDD GREEN phase: implement minimal code passing all 11 RED tests
    - re.fullmatch() name validation before any Path operation (T-02-01 path traversal mitigation)
    - _SKILLS_ROOT module-level Path resolved at import time for test isolation
    - JSON envelope pattern: {"output": {...}, "reasoning": "...", "confidence": 0.0}
    - Pydantic model_validate() for untrusted LLM output validation

key-files:
  created: []
  modified:
    - backend/app/infrastructure/skills/loader.py

key-decisions:
  - "re.fullmatch(r'^[a-z0-9][a-z0-9-]*$') validates skill_name before any filesystem operation — path traversal characters are rejected before Path arithmetic"
  - "importlib.util.spec_from_file_location loads schema .py files by absolute path — no sys.path modification needed for kebab-named directories"
  - "_parse_skill_md() uses re.search(DOTALL) for system prompt extraction — tolerates arbitrary content between front matter and System Prompt section"
  - "_parse_llm_response() strips markdown code fences before JSON parsing — same pattern as classification_agent.py for consistency"

requirements-completed:
  - SKILL-02

# Metrics
duration: 1min
completed: 2026-04-13
---

# Phase 02 Plan 02: Skill Loader Implementation (GREEN) Summary

**Dynamic filesystem skill loader using importlib.util — discovers skills by kebab-case directory name, validates names with re.fullmatch(), loads schema classes by absolute path, and executes them via a JSON envelope protocol with Pydantic model_validate()**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-13T14:49:41Z
- **Completed:** 2026-04-13T14:51:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Implemented `load_skill()` — validates skill_name with `re.fullmatch(r'^[a-z0-9][a-z0-9-]*$')` before any filesystem operation (T-02-01 path traversal mitigation), then locates the skill directory under `_SKILLS_ROOT`, checks for `SKILL.md`, and dynamically loads `input_schema.py` / `output_schema.py`
- Implemented `_load_schema_class()` — uses `importlib.util.spec_from_file_location` by absolute path so kebab-named directories (invalid Python identifiers) are handled without any `sys.path` manipulation
- Implemented `SkillRunner.run()` — serializes input to JSON, appends `_ENVELOPE_INSTRUCTIONS` to the system prompt, calls the LLM client, then parses and validates the response with `_parse_llm_response()`
- Implemented `_parse_skill_md()` — extracts YAML front matter between `---` delimiters and system prompt from the fenced block under `## System Prompt`
- Implemented `_parse_llm_response()` — strips optional markdown code fences, JSON-parses the envelope, then validates the `"output"` value with `output_schema_class.model_validate()` — raises `SkillMalformedError` on any parse or validation failure
- All 11 SKILL-02 RED tests now pass GREEN; full suite of 58 tests passes with 0 regressions

## Task Commits

1. **Task 1: Implement full loader.py — load_skill(), SkillRunner, SkillResult** - `a9af531` (feat)

## Files Created/Modified

- `backend/app/infrastructure/skills/loader.py` — complete implementation replacing `NotImplementedError` stubs; 245 lines; exports `load_skill`, `SkillRunner`, `SkillResult`, `_SKILLS_ROOT`

## Decisions Made

- `re.fullmatch(r'^[a-z0-9][a-z0-9-]*$')` validates before any `Path` arithmetic — characters `../`, `\`, spaces, uppercase all rejected; raises `SkillNotFoundError` on mismatch (matches T-02-01 threat mitigation from plan)
- `importlib.util.spec_from_file_location` loads schema files by absolute path — no `sys.path` manipulation required for kebab-named directories which are invalid Python package identifiers
- Code-fence stripping in `_parse_llm_response()` adopted from `classification_agent.py` pattern for consistency across LLM response parsing in the codebase
- `_ENVELOPE_INSTRUCTIONS` appended to every skill system prompt ensures the LLM always returns the three-field JSON envelope without per-skill prompt boilerplate

## Deviations from Plan

None — plan executed exactly as written. The implementation provided verbatim in the plan action block was used without modification.

## Known Stubs

None. All `NotImplementedError` stubs from Wave 0 (Plan 02-01) have been replaced with complete implementations.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced beyond what was described in the plan's `<threat_model>`. The `exec_module` call on schema `.py` files is intentionally scoped to first-party repository paths with no user input reaching that code path (T-02-02 accepted disposition).

## Self-Check

- `backend/app/infrastructure/skills/loader.py` exists: FOUND
- `loader.py` contains `_SKILLS_ROOT = Path(__file__).resolve().parents[3] / "skills"`: FOUND
- `loader.py` contains `_SKILL_NAME_RE = re.compile(`: FOUND
- `loader.py` contains `def load_skill(skill_name: str) -> SkillRunner:`: FOUND
- `loader.py` contains `def _load_schema_class(`: FOUND
- `loader.py` contains `spec_from_file_location`: FOUND
- `loader.py` contains `model_validate`: FOUND
- `loader.py` contains `_ENVELOPE_INSTRUCTIONS`: FOUND
- Commit `a9af531` exists: FOUND

## Self-Check: PASSED

---
*Phase: 02-skill-loader*
*Completed: 2026-04-13*
