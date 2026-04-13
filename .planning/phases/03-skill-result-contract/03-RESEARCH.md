# Phase 3: Skill Result Contract - Research

**Researched:** 2026-04-13
**Domain:** Python dataclass validation, Pydantic, pytest parametrization, public package API surface
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** All three envelope fields — `output`, `reasoning`, `confidence` — are **required**. Any JSON response missing any of these keys raises `SkillMalformedError`. Silent defaults (`""`, `0.0`) introduced in Phase 2 are removed.
- **D-02:** `reasoning` must be a **non-empty string** (non-empty after `.strip()`). An empty or whitespace-only reasoning string is treated as a contract violation and raises `SkillMalformedError`.
- **D-03:** `confidence` must be a **numeric value in `[0.0, 1.0]`** inclusive. Values outside this range raise `SkillMalformedError`. The value `0.0` is allowed. Non-numeric values (e.g. `"high"`) also raise `SkillMalformedError`.
- **D-04:** Phase 3 populates `app/infrastructure/skills/__init__.py` with explicit re-exports and `__all__`:
  ```python
  __all__ = ["SkillResult", "SkillRunner", "load_skill", "SkillNotFoundError", "SkillMalformedError"]
  ```

### Claude's Discretion

- Whether `_parse_llm_response()` in `loader.py` is modified in-place or refactored into a separate `_validate_envelope()` helper (recommended: separate helper)
- Whether `SkillMalformedError` messages for each new validation scenario use structured field names (e.g. `"reasoning field is empty"`) — follow existing error message patterns

### Deferred Ideas (OUT OF SCOPE)

- None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKILL-03 | skill 调用结果统一封装，含 structured output、reasoning、confidence | Envelope strictness validation patterns, `_validate_envelope()` helper design, `__init__.py` re-export pattern, parametrized tests for all rejection scenarios |
</phase_requirements>

---

## Summary

Phase 3 is a gatekeeper phase, not a builder phase. Phase 2 already created `SkillResult`, `SkillRunner`, `load_skill`, `SkillNotFoundError`, and `SkillMalformedError` in `backend/app/infrastructure/skills/loader.py`. All 11 Phase 2 tests pass. The current `_parse_llm_response()` function uses lenient defaults (`data.get("reasoning", "")`, `float(data.get("confidence", 0.0))`) which silently accept missing fields. Phase 3 replaces these with strict presence checks and adds range validation for `confidence`.

The work is contained in three files: `loader.py` (validation logic), `__init__.py` (public API surface), and a new test block in `test_skill_loader.py`. No schema files, no database changes, no API routes, no UI. The scope is deliberately narrow.

**Primary recommendation:** Extract a `_validate_envelope()` helper from `_parse_llm_response()` so envelope validation is isolated, testable in isolation, and clearly separate from JSON parsing and schema validation. Write parametrized tests covering all five new rejection scenarios (missing output, missing reasoning, missing confidence, empty reasoning, out-of-range confidence).

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses | stdlib | `SkillResult` container | Already used in Phase 2 — no change |
| Pydantic v2 | `>=2.12.5` | Output schema validation in `_parse_llm_response` | Project standard for all validation |
| pytest | `>=9.0.2` | Test framework | Project standard, confirmed in pyproject.toml |

[VERIFIED: pyproject.toml] — exact versions from project dependency lock file.

### No New Dependencies

Phase 3 adds zero new packages. All validation logic uses Python stdlib (`isinstance`, `float`, `str.strip`) and the already-imported `SkillMalformedError`. [VERIFIED: loader.py lines 1–23]

---

## Architecture Patterns

### Recommended Project Structure

Phase 3 touches exactly these files:

```
backend/
├── app/
│   └── infrastructure/
│       └── skills/
│           ├── __init__.py       # Phase 3 populates (currently empty)
│           └── loader.py         # Phase 3 modifies _parse_llm_response()
└── tests/
    └── test_skill_loader.py      # Phase 3 adds new test block
```

No new files created. No files deleted.

### Pattern 1: Extract `_validate_envelope()` Helper

**What:** Pull the three-field validation logic out of `_parse_llm_response()` into a dedicated helper. `_parse_llm_response()` calls it after `json.loads()` succeeds.

**When to use:** Recommended by CONTEXT.md and good TDD hygiene — the validator can be unit-tested directly with a dict, without mocking an LLM response string.

**Current lenient code (to replace):**

```python
# Source: backend/app/infrastructure/skills/loader.py lines 270-278
reasoning = str(data.get("reasoning", ""))
confidence = float(data.get("confidence", 0.0))
```

**After Phase 3 — strict pattern:**

```python
# _validate_envelope() — called from _parse_llm_response() after json.loads()
def _validate_envelope(skill_name: str, data: dict) -> tuple[Any, str, float]:
    """
    Enforce the three-field result contract. Raises SkillMalformedError for any violation.
    """
    # D-01: all three keys must be present
    for key in ("output", "reasoning", "confidence"):
        if key not in data:
            raise SkillMalformedError(skill_name, f"missing required envelope field: {key!r}")

    # D-02: reasoning must be a non-empty string after strip
    reasoning = data["reasoning"]
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise SkillMalformedError(skill_name, "reasoning field is empty or non-string")

    # D-03: confidence must be numeric in [0.0, 1.0]
    confidence_raw = data["confidence"]
    if not isinstance(confidence_raw, (int, float)) or isinstance(confidence_raw, bool):
        raise SkillMalformedError(skill_name, f"confidence field is not numeric: {confidence_raw!r}")
    confidence = float(confidence_raw)
    if not (0.0 <= confidence <= 1.0):
        raise SkillMalformedError(skill_name, f"confidence {confidence} is outside [0.0, 1.0]")

    return data["output"], reasoning, confidence
```

[ASSUMED] — this exact implementation is derived from the locked decisions in CONTEXT.md and Python stdlib behavior; the code was not in the repo at research time.

**Important detail on `bool` exclusion:** In Python, `bool` is a subclass of `int`, so `isinstance(True, (int, float))` returns `True`. The `isinstance(confidence_raw, bool)` guard prevents `True`/`False` from passing as valid confidence values, since they are not semantically meaningful as floats. [VERIFIED: Python stdlib behavior — bool inherits from int]

### Pattern 2: Updated `_parse_llm_response()` Flow

**What:** After JSON parse succeeds, delegate envelope validation to `_validate_envelope()`, then proceed with output schema validation as before.

```python
def _parse_llm_response(
    skill_name: str, text: str, output_schema_class: type
) -> tuple[Any, str, float]:
    # ... (markdown fence stripping, json.loads — unchanged) ...

    output_raw, reasoning, confidence = _validate_envelope(skill_name, data)

    try:
        structured_output = output_schema_class.model_validate(output_raw)
    except ValidationError as exc:
        raise SkillMalformedError(
            skill_name, f"LLM output failed schema validation: {exc}"
        ) from exc

    return structured_output, reasoning, confidence
```

[ASSUMED] — derived from existing code structure at loader.py lines 241–279.

### Pattern 3: `__init__.py` Public API

**What:** Re-export all public symbols from `loader.py` and `app.core.exceptions` via the package `__init__.py`.

**Current state:** `__init__.py` is a 0-byte empty file. [VERIFIED: directory listing — file size 0]

**After Phase 3:**

```python
# Source: app/infrastructure/skills/__init__.py — Phase 3 creates this content
"""Public API for the skills infrastructure package."""

from app.core.exceptions import SkillMalformedError, SkillNotFoundError
from app.infrastructure.skills.loader import SkillResult, SkillRunner, load_skill

__all__ = [
    "SkillResult",
    "SkillRunner",
    "load_skill",
    "SkillNotFoundError",
    "SkillMalformedError",
]
```

After this, downstream callers (Phases 5 and 8) can write:
```python
from app.infrastructure.skills import SkillResult, load_skill
```

[ASSUMED] — content derived directly from D-04 in CONTEXT.md.

### Pattern 4: Parametrized Rejection Tests

**What:** Following the existing test patterns in `test_skill_loader.py`, use `pytest.mark.parametrize` to cover all envelope rejection scenarios in a single test function.

**Existing precedent:** `test_skill_runner_schema_validation_failure` (line 212) shows the in-memory `SkillRunner` construction pattern — reused for new tests.

**New test block structure:**

```python
# Source: test_skill_loader.py — new block added by Phase 3

@pytest.mark.parametrize("bad_response,expected_detail_fragment", [
    # D-01: missing keys
    (json.dumps({"reasoning": "ok", "confidence": 0.5}),                  "output"),
    (json.dumps({"output": {}, "confidence": 0.5}),                       "reasoning"),
    (json.dumps({"output": {}, "reasoning": "ok"}),                       "confidence"),
    # D-02: empty/whitespace reasoning
    (json.dumps({"output": {}, "reasoning": "", "confidence": 0.5}),      "reasoning"),
    (json.dumps({"output": {}, "reasoning": "   ", "confidence": 0.5}),   "reasoning"),
    # D-03: out-of-range / non-numeric confidence
    (json.dumps({"output": {}, "reasoning": "ok", "confidence": -0.1}),   "confidence"),
    (json.dumps({"output": {}, "reasoning": "ok", "confidence": 1.1}),    "confidence"),
    (json.dumps({"output": {}, "reasoning": "ok", "confidence": "high"}), "confidence"),
])
def test_skill_runner_envelope_contract_violations(bad_response, expected_detail_fragment):
    """Any envelope contract violation raises SkillMalformedError."""
    runner = _make_passthrough_runner()
    with pytest.raises(SkillMalformedError) as exc_info:
        runner.run(MockLLMClient(bad_response), {})
    assert expected_detail_fragment in exc_info.value.detail
```

The `_make_passthrough_runner()` helper builds a `SkillRunner` with an empty `BaseModel` output schema (identical to the approach in `test_skill_runner_schema_validation_failure`). [ASSUMED] — derived from existing test patterns in Phase 2.

### Anti-Patterns to Avoid

- **Silent default substitution:** `data.get("reasoning", "")` — this is the pattern Phase 3 explicitly replaces. Never use default values for envelope fields.
- **Catching broad `Exception` in `_validate_envelope`:** Envelope validation raises `SkillMalformedError` directly. No try/except needed around the field presence checks.
- **Type coercion before type check:** Do not call `float(data.get("confidence"))` before checking if the key exists — this masks `KeyError` with a misleading `TypeError`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Numeric range check | Custom range validator class | `0.0 <= confidence <= 1.0` Python chained comparison | Python chained comparison is idiomatic, readable, zero dependencies |
| Type check for numeric | `try: float(v)` | `isinstance(v, (int, float)) and not isinstance(v, bool)` | `float()` coerces strings like `"0.5"` — not wanted here |
| Re-export pattern | Repeating import logic | `__all__` with explicit names in `__init__.py` | Standard Python package public API pattern |

---

## Common Pitfalls

### Pitfall 1: `bool` passes `isinstance(x, (int, float))`

**What goes wrong:** `confidence = True` passes `isinstance(True, (int, float))` and `float(True) == 1.0`. A boolean confidence value would silently be accepted.

**Why it happens:** `bool` is a subclass of `int` in Python.

**How to avoid:** Add `and not isinstance(confidence_raw, bool)` to the type guard. [VERIFIED: Python stdlib — bool inherits from int]

**Warning signs:** Tests pass `True` or `False` as confidence and no error is raised.

### Pitfall 2: Removing the Silent Default Breaks Existing Happy-Path Tests

**What goes wrong:** The existing Phase 2 test `test_skill_runner_run_returns_result` passes a `valid_response` that includes all three fields. It will continue to pass after Phase 3 changes — no action needed.

**Why it's mentioned:** Phase 3 removes the `data.get("reasoning", "")` fallback. Tests that pass well-formed responses are unaffected. Only tests for malformed responses change behavior.

**Warning signs:** If any Phase 2 tests start failing after Phase 3 changes, the valid_response payloads are likely missing a field — check their fixture JSON.

**Status:** Verified by reading all Phase 2 test fixtures — all include all three fields explicitly. [VERIFIED: test_skill_loader.py lines 184–189, 232–236]

### Pitfall 3: Circular Import in `__init__.py`

**What goes wrong:** `__init__.py` imports from `loader.py`; if `loader.py` ever imports from the package (`from app.infrastructure.skills import ...`), a circular import results.

**Why it happens:** Package-level re-exports create a two-way dependency when implementation modules import from their own package.

**How to avoid:** `loader.py` imports from `app.core.exceptions` directly (not from the package `__init__.py`). This is already the pattern — `loader.py` line 21: `from app.core.exceptions import SkillMalformedError, SkillNotFoundError`. [VERIFIED: loader.py line 21]

**Warning signs:** `ImportError: cannot import name 'SkillMalformedError'` at test startup.

### Pitfall 4: `assert expected_detail_fragment in exc_info.value.detail` Relies on `SkillMalformedError.detail`

**What goes wrong:** The test assertion uses `.detail` attribute — this only works because `SkillMalformedError.__init__` stores `self.detail = detail`. [VERIFIED: backend/app/core/exceptions.py lines 41–47]

**How to avoid:** Use `.detail` (not `.args[0]` or `str(exc)`) in test assertions to stay consistent with existing Phase 2 tests.

---

## Code Examples

### Existing `SkillMalformedError` Signature

```python
# Source: backend/app/core/exceptions.py lines 41–47
class SkillMalformedError(BeancountBotError):
    """Skill directory found but files are missing or invalid."""

    def __init__(self, skill_name: str, detail: str) -> None:
        self.skill_name = skill_name
        self.detail = detail
        super().__init__(f"Skill {skill_name!r} is malformed: {detail}")
```

New Phase 3 `SkillMalformedError` raises follow the exact same two-argument call signature. No changes to the exception class itself.

### Current Lenient Lines (to replace)

```python
# Source: backend/app/infrastructure/skills/loader.py lines 270-278
# These two lines are the only changes to the existing happy-path logic:
reasoning = str(data.get("reasoning", ""))      # <- replace with strict check
confidence = float(data.get("confidence", 0.0)) # <- replace with strict check
```

### Existing MockLLMClient Fixture (reuse for new tests)

```python
# Source: backend/tests/test_skill_loader.py lines 25–32
@dataclass
class MockLLMClient:
    """Duck-typed LLMAdapter for unit tests — no real HTTP calls."""

    response_text: str

    def complete(self, messages: list[LLMMessage], system: str = "") -> LLMCompletion:
        return LLMCompletion(text=self.response_text, usage=LLMUsage())
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Silent defaults `data.get("reasoning", "")` | Strict presence + type + value checks | Phase 3 | Missing fields are detected at skill boundary instead of silently propagating |
| `loader.py` is the only import path | `__init__.py` re-exports public surface | Phase 3 | Downstream phases (5, 8) import from `app.infrastructure.skills` without knowing internal file layout |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_validate_envelope()` helper code pattern shown in Architecture Patterns | Architecture Patterns | If Python type system behaves differently than expected — unlikely but planner should verify bool-exclusion logic |
| A2 | `__init__.py` re-export content as shown | Architecture Patterns | If there are circular import issues not anticipated — mitigated by Pitfall 3 analysis |
| A3 | Parametrized test structure with `_make_passthrough_runner()` helper | Architecture Patterns | Helper function name is illustrative; planner should use the same inline `SkillRunner(...)` pattern as Phase 2 test line 225 |

---

## Open Questions

None. All decisions are locked in CONTEXT.md. The implementation is fully specified by the three locked decisions and the existing code structure.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 3 is a pure code/test change. No external dependencies, services, or CLI tools beyond the existing Python + pytest stack (already confirmed working — all 11 Phase 2 tests pass).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `backend/pyproject.toml` (configfile confirmed by pytest output) |
| Quick run command | `cd backend && uv run pytest tests/test_skill_loader.py -v` |
| Full suite command | `cd backend && uv run pytest -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILL-03 | Missing `output` key raises SkillMalformedError | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 |
| SKILL-03 | Missing `reasoning` key raises SkillMalformedError | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 |
| SKILL-03 | Missing `confidence` key raises SkillMalformedError | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 |
| SKILL-03 | Empty `reasoning` string raises SkillMalformedError | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 |
| SKILL-03 | Whitespace-only `reasoning` raises SkillMalformedError | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 |
| SKILL-03 | `confidence < 0.0` raises SkillMalformedError | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 |
| SKILL-03 | `confidence > 1.0` raises SkillMalformedError | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 |
| SKILL-03 | Non-numeric `confidence` raises SkillMalformedError | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 |
| SKILL-03 | `from app.infrastructure.skills import SkillResult, load_skill` works | unit | `uv run pytest tests/test_skill_loader.py -k "public_api" -v` | ❌ Wave 0 |
| SKILL-03 | Existing Phase 2 happy-path tests still pass | regression | `uv run pytest tests/test_skill_loader.py -v` | ✅ Exists |

### Sampling Rate

- **Per task commit:** `cd backend && uv run pytest tests/test_skill_loader.py -v`
- **Per wave merge:** `cd backend && uv run pytest -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] New test block in `backend/tests/test_skill_loader.py` — parametrized envelope contract violation tests (8 rejection scenarios + 1 public API import test) — covers all SKILL-03 behaviors listed above

*(Existing test infrastructure is in place. Only new test cases need to be added to the existing file.)*

---

## Security Domain

Phase 3 adds no new user inputs, no API endpoints, no database operations, and no external calls. The existing path-traversal guard in `load_skill()` (line 143: `_SKILL_NAME_RE.fullmatch`) is unchanged. No ASVS categories apply to this phase.

---

## Sources

### Primary (HIGH confidence)

- `backend/app/infrastructure/skills/loader.py` — current implementation, lines 241–279 (`_parse_llm_response`), lines 59–65 (`SkillResult`), line 21 (exceptions import)
- `backend/app/core/exceptions.py` — `SkillMalformedError` and `SkillNotFoundError` definitions
- `backend/tests/test_skill_loader.py` — Phase 2 test patterns, `MockLLMClient`, in-memory `SkillRunner` construction
- `backend/app/infrastructure/skills/__init__.py` — confirmed empty (0 bytes)
- `.planning/phases/03-skill-result-contract/03-CONTEXT.md` — locked decisions D-01 through D-04
- Python stdlib documentation — `bool` inherits from `int`: confirmed by Python language spec

### Secondary (MEDIUM confidence)

- `.planning/phases/02-skill-loader/02-CONTEXT.md` — D-04 (Phase 3 role clarification), carried-forward decisions

### Tertiary (LOW confidence)

- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all tools verified in pyproject.toml and test run output
- Architecture: HIGH — all patterns derived from existing verified code; only the `bool` exclusion logic is [ASSUMED] but well-supported by Python stdlib
- Pitfalls: HIGH — derived from reading actual code and existing test patterns; verified against live test run

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable domain — Python stdlib + project-internal code, no external ecosystem churn)
