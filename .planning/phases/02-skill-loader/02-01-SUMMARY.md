---
phase: 02-skill-loader
plan: 01
subsystem: testing
tags: [pytest, tdd, skill-loader, exceptions, python]

# Dependency graph
requires:
  - phase: 01-skill-directory-scaffold
    provides: backend/skills/cross-channel-dedup/ directory with SKILL.md, input_schema.py, output_schema.py
provides:
  - 11 failing pytest tests defining the load_skill() / SkillRunner / SkillResult behavior contract
  - SkillNotFoundError and SkillMalformedError exception types in app.core.exceptions
  - backend/app/infrastructure/skills/ Python package with loader.py stub
affects:
  - 02-02 (Wave 1 implementation turns these RED tests GREEN)
  - 03-skill-result-contract (depends on SkillResult dataclass shape)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD RED phase: write failing tests first, stub raises NotImplementedError so imports resolve
    - _SKILLS_ROOT module-level variable on loader for test isolation via patch.object
    - MockLLMClient as in-test dataclass duck-typing LLMAdapter Protocol

key-files:
  created:
    - backend/tests/test_skill_loader.py
    - backend/app/infrastructure/skills/__init__.py
    - backend/app/infrastructure/skills/loader.py
  modified:
    - backend/app/core/exceptions.py

key-decisions:
  - "loader.py exposes _SKILLS_ROOT at module level so tests can patch it without changing production code paths"
  - "SkillRunner.run() wraps LLM response in a JSON envelope with 'output', 'reasoning', 'confidence' keys"
  - "Skill name validation (re.fullmatch pattern) is tested via test_load_skill_validates_name — Wave 1 must implement"

patterns-established:
  - "Skill isolation: tmp_path + patch.object(loader_module, '_SKILLS_ROOT', tmp_path) for hermetic tests"
  - "Error hierarchy: SkillNotFoundError (missing dir) vs SkillMalformedError (malformed content) both under BeancountBotError"

requirements-completed:
  - SKILL-02

# Metrics
duration: 8min
completed: 2026-04-13
---

# Phase 02 Plan 01: Skill Loader TDD Red Phase Summary

**11 failing pytest tests defining the load_skill() behavior contract, plus SkillNotFoundError/SkillMalformedError exception types and an empty loader stub — all imports resolve, all 11 tests fail (RED)**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-13T14:45:00Z
- **Completed:** 2026-04-13T14:53:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added `SkillNotFoundError` and `SkillMalformedError` to `app.core.exceptions` with correct message formats and `.skill_name` / `.detail` attributes
- Created `backend/app/infrastructure/skills/` Python package with a `loader.py` stub that defines `load_skill()`, `SkillRunner`, and `SkillResult` — all importable, all raising `NotImplementedError`
- Wrote 11 failing unit tests in `test_skill_loader.py` covering happy path (load real skill, load via patched root), 5 error paths (not found, missing files, wrong class name, path traversal), and 3 SkillRunner.run() cases (valid JSON envelope, non-JSON, schema validation failure)
- Phase 1 tests (`test_skill_scaffold.py`) still pass — no regression

## Task Commits

Each task was committed atomically:

1. **Task 1: Add SkillNotFoundError and SkillMalformedError to exceptions.py** - `0b96a63` (feat)
2. **Task 2: Create skills/ sub-package and empty loader stub** - `faed705` (feat)
3. **Task 3: Write 11 failing tests in test_skill_loader.py (RED phase)** - `16eaaf9` (test)

_Note: This is a TDD RED phase — task 3 test commit is intentionally failing._

## Files Created/Modified

- `backend/app/core/exceptions.py` — appended `SkillNotFoundError(skill_name)` and `SkillMalformedError(skill_name, detail)` inheriting from `BeancountBotError`
- `backend/app/infrastructure/skills/__init__.py` — empty Python package marker
- `backend/app/infrastructure/skills/loader.py` — stub: `SkillResult` dataclass, `SkillRunner` class with stub `run()`, `load_skill()` stub; imports error types; exposes `_SKILLS_ROOT` for test patching
- `backend/tests/test_skill_loader.py` — 11 test functions; `MockLLMClient` dataclass; `_make_minimal_skill()` fixture helper

## Decisions Made

- `_SKILLS_ROOT` module-level `Path` variable in `loader.py` enables `patch.object()` isolation in tests without changing production code paths
- `SkillRunner.run()` response envelope uses `{"output": ..., "reasoning": ..., "confidence": ...}` JSON structure (tested by `test_skill_runner_run_returns_result`)
- Skill name validation tested via `test_load_skill_validates_name` with `"../etc/passwd"` — Wave 1 must implement `re.fullmatch(r'[a-z0-9-]+', skill_name)` guard (T-02-01 threat mitigation)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — the worktree required a `git checkout HEAD -- .` to restore files after the initial `git reset --soft` during branch alignment, but this was a setup step, not an execution issue.

## User Setup Required

None — no external service configuration required.

## Known Stubs

- `backend/app/infrastructure/skills/loader.py` — `load_skill()` raises `NotImplementedError` intentionally. Wave 1 (02-02-PLAN.md) implements the full loader.
- `backend/app/infrastructure/skills/loader.py` — `SkillRunner.run()` raises `NotImplementedError` intentionally. Wave 1 implements this too.

These stubs are intentional RED-phase artifacts; Wave 1 replaces them with real implementations.

## Next Phase Readiness

- Wave 1 (Plan 02-02) can begin immediately — 11 failing tests define the exact contract to satisfy
- `_SKILLS_ROOT` patching pattern is established; Wave 1 must assign it a real `Path` pointing to `backend/skills/`
- All imports resolve — Wave 1 only needs to implement, not restructure

## Self-Check

- `backend/tests/test_skill_loader.py` exists: FOUND
- `backend/app/core/exceptions.py` contains `SkillNotFoundError`: FOUND
- `backend/app/infrastructure/skills/__init__.py` exists: FOUND
- `backend/app/infrastructure/skills/loader.py` contains `load_skill`: FOUND
- Commits `0b96a63`, `faed705`, `16eaaf9` verified: FOUND

## Self-Check: PASSED

---
*Phase: 02-skill-loader*
*Completed: 2026-04-13*
