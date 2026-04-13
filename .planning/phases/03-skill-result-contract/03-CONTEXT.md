# Phase 3: Skill Result Contract - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Strengthen and enforce the `SkillResult(structured_output, reasoning, confidence)` envelope
contract so that every skill invocation either returns a fully-populated, validated result or
raises `SkillMalformedError`. Phase 3 is the **gatekeeper**, not the initial implementor —
`SkillResult` and `SkillRunner.run()` were created in Phase 2; this phase makes the contract
verifiably enforced and exposes a clean public API surface for downstream phases.

Phase 3 delivers:
1. Strict three-field envelope validation: all three keys (`output`, `reasoning`, `confidence`) must be present and valid — missing or degenerate values are rejected
2. Confidence bounds enforcement: `confidence` must be a numeric value in `[0.0, 1.0]`
3. Non-empty `reasoning` enforcement: empty string after strip is a contract violation
4. Public `__init__.py` exports: `from app.infrastructure.skills import SkillResult, SkillRunner, load_skill, SkillNotFoundError, SkillMalformedError`
5. New test coverage for all enforcement scenarios added in this phase

**NOT in scope for Phase 3:**
- Filling in actual skill prompts or schema fields (Phase 4)
- Running skills inside the import pipeline (Phase 5)
- Any UI changes

</domain>

<decisions>
## Implementation Decisions

### Envelope Field Strictness
- **D-01:** All three envelope fields — `output`, `reasoning`, `confidence` — are **required**.
  Any JSON response missing any of these keys raises `SkillMalformedError`. Silent defaults
  (`""`, `0.0`) introduced in Phase 2 are removed.
- **D-02:** `reasoning` must be a **non-empty string** (non-empty after `.strip()`). An empty
  or whitespace-only reasoning string is treated as a contract violation and raises
  `SkillMalformedError`. Rationale: downstream workflows need reasoning for debugging and
  audit; a blank string provides no value.

### Confidence Bounds
- **D-03:** `confidence` must be a **numeric value in `[0.0, 1.0]`** inclusive. Values outside
  this range raise `SkillMalformedError`. The value `0.0` is allowed (LLM may legitimately
  have zero confidence). Non-numeric values (e.g. `"high"`) also raise `SkillMalformedError`.

### Public Import Surface
- **D-04:** Phase 3 establishes a clean public API by populating
  `app/infrastructure/skills/__init__.py` with explicit re-exports and `__all__`:
  ```python
  __all__ = ["SkillResult", "SkillRunner", "load_skill", "SkillNotFoundError", "SkillMalformedError"]
  ```
  After this phase, downstream callers (Phases 5, 8) import from:
  ```python
  from app.infrastructure.skills import SkillResult, load_skill
  ```
  The `loader.py` module remains the implementation file but is an internal detail.

### Claude's Discretion
- Whether `_parse_llm_response()` in `loader.py` is modified in-place or refactored into a
  separate `_validate_envelope()` helper (recommended: separate helper — makes the validation
  logic testable in isolation)
- Whether `SkillMalformedError` messages for each new validation scenario use structured
  field names (e.g. `"reasoning field is empty"`) — follow existing error message patterns

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — SKILL-03 requirement (Chinese text, authoritative)
- `.planning/ROADMAP.md` — Phase 3 success criteria (4 items); Phase 5 and 8 context
  (will depend on `SkillResult` being trustworthy)

### Phase 1 & 2 Context (locked decisions carried forward)
- `.planning/phases/01-skill-directory-scaffold/01-CONTEXT.md` — file format, Pydantic schemas,
  kebab naming (all pre-answered)
- `.planning/phases/02-skill-loader/02-CONTEXT.md` — `SkillResult` definition, `SkillRunner.run()`
  contract, `SkillMalformedError` as the rejection exception (D-04 specifically: Phase 3 role)

### Implementation Files (must read before modifying)
- `backend/app/infrastructure/skills/loader.py` — current `_parse_llm_response()`, `SkillResult`,
  `_ENVELOPE_INSTRUCTIONS`; Phase 3 modifies this file
- `backend/app/infrastructure/skills/__init__.py` — currently empty; Phase 3 populates it
- `backend/app/core/exceptions.py` — `SkillMalformedError`, `SkillNotFoundError` definitions
- `backend/tests/test_skill_loader.py` — Phase 2 tests; Phase 3 adds new tests alongside these

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_parse_llm_response()` in `loader.py` (lines 241–279) — current validation logic; Phase 3
  extends this to enforce D-01, D-02, D-03
- `SkillMalformedError` in `app/core/exceptions.py` — already used for JSON parse failures
  and schema validation failures; extend same exception for envelope strictness failures

### Established Patterns
- **Missing key detection:** `data.get("reasoning", "")` is the current lenient pattern to
  replace with explicit key presence checks (`"reasoning" not in data`)
- **Validation error messages:** existing `SkillMalformedError` messages follow the pattern
  `"LLM returned non-JSON: {exc}"` — Phase 3 adds similar messages for field-level failures
- **Test fixture pattern:** `test_skill_runner_schema_validation_failure` in `test_skill_loader.py`
  shows how to build an in-memory `SkillRunner` without loading from disk — reuse for new tests

### Integration Points
- Phase 5 (dedup gate) and Phase 8 (transfer pipeline) will `from app.infrastructure.skills import load_skill, SkillResult`
  — this is the import path Phase 3 must stabilize

</code_context>

<specifics>
## Specific Ideas

- The `_ENVELOPE_INSTRUCTIONS` injected into system prompts already instructs the LLM to
  return all three fields. Phase 3's validation now enforces what those instructions request.
- New tests should mirror the structure of Phase 2 tests — parametrize across failure modes
  rather than writing one test per case where scenarios can be grouped.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-skill-result-contract*
*Context gathered: 2026-04-13*
