# Phase 3: Skill Result Contract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 03-skill-result-contract
**Areas discussed:** Envelope strictness, Confidence bounds, Public import surface

---

## Envelope Strictness

| Option | Description | Selected |
|--------|-------------|----------|
| Strict — all three required | All three fields (output, reasoning, confidence) must be present. Any missing field raises SkillMalformedError. | ✓ |
| Lenient — only output required | Only 'output' is required; reasoning/confidence can be absent and default. | |

**User's choice:** Strict — all three required

**Notes:** Success criterion 3 ("invalid model output is rejected as a skill-contract failure") was the explicit rationale. Silent defaults undermine the contract guarantees downstream phases rely on.

---

### Follow-up: Empty reasoning

| Option | Description | Selected |
|--------|-------------|----------|
| Non-empty string required | reasoning must be non-empty after strip. Empty string is a contract violation. | ✓ |
| Present but can be empty | reasoning just has to be a string key. Empty string allowed. | |

**User's choice:** Non-empty string required

**Notes:** Preserves usefulness for debugging — a blank reasoning provides no value to downstream workflows that preserve it for audit/review.

---

## Confidence Bounds

| Option | Description | Selected |
|--------|-------------|----------|
| Strict [0.0, 1.0] range | confidence must be in [0.0, 1.0]. Out-of-range raises SkillMalformedError. | ✓ |
| Clamp silently | Out-of-range values corrected rather than rejected. | |
| Any float accepted | No bounds check. | |

**User's choice:** Strict [0.0, 1.0] range

---

### Follow-up: Zero confidence

| Option | Description | Selected |
|--------|-------------|----------|
| Number in [0.0, 1.0] only | Only check number + range. 0.0 is allowed. | ✓ |
| Positive float in (0.0, 1.0] | Zero means no confidence — treated as contract failure. | |

**User's choice:** Number in [0.0, 1.0] only (zero is allowed)

---

## Public Import Surface

| Option | Description | Selected |
|--------|-------------|----------|
| Public __init__.py exports | Re-export from app/infrastructure/skills/__init__.py with __all__. | ✓ |
| Keep in loader.py only | Leave SkillResult in loader.py. Callers import from full path. | |

**User's choice:** Public __init__.py exports

---

### Follow-up: What to export

| Option | Description | Selected |
|--------|-------------|----------|
| Full public surface | SkillResult, SkillRunner, load_skill, SkillNotFoundError, SkillMalformedError | ✓ |
| Minimal (SkillResult + load_skill only) | Only what downstream phases need immediately | |

**User's choice:** Full public surface

---

## Claude's Discretion

- Internal refactoring of `_parse_llm_response()` (whether to extract `_validate_envelope()` helper)
- Error message wording for new validation failures
- Test parametrization strategy for multiple failure modes

## Deferred Ideas

None — discussion stayed within phase scope.
