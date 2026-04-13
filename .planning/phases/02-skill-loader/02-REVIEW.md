---
phase: 02-skill-loader
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - backend/app/core/exceptions.py
  - backend/app/infrastructure/skills/__init__.py
  - backend/app/infrastructure/skills/loader.py
  - backend/tests/test_skill_loader.py
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

The skill loader implementation is solid overall: the path-traversal guard (`_SKILL_NAME_RE`), the `importlib.util` dynamic loading approach, and the structured exception hierarchy are all well-designed. The `SkillRunner` / `SkillResult` dataclass split is clean and the test suite covers the primary happy-path and error-path cases comprehensively.

Three warnings were found, all in `loader.py`. None are security vulnerabilities (the path-traversal guard is correct), but two can produce silent, hard-to-diagnose runtime failures: an empty system prompt silently accepted as valid, and non-Pydantic classes passing the schema loading step. A third issue is that the LLM confidence value is accepted without range validation.

---

## Warnings

### WR-01: Silent empty system prompt accepted as valid skill

**File:** `backend/app/infrastructure/skills/loader.py:235-236`
**Issue:** `_parse_skill_md` uses a regex to locate the `## System Prompt` fenced block. When the block is absent (typo in heading, wrong fence style, etc.), `system_prompt` silently becomes `""`. `load_skill()` returns a `SkillRunner` without raising `SkillMalformedError`, and every subsequent `run()` call sends a blank system prompt to the LLM, producing garbage output with no diagnostic trace back to the malformed skill file.

**Fix:**
```python
# _parse_skill_md, after line 236:
match = re.search(r"## System Prompt\s*\n+```[^\n]*\n(.*?)```", text, re.DOTALL)
if match is None:
    raise SkillMalformedError(
        skill_name, "SKILL.md missing '## System Prompt' fenced block"
    )
system_prompt = match.group(1).strip()
```

---

### WR-02: Schema class not validated as Pydantic BaseModel

**File:** `backend/app/infrastructure/skills/loader.py:200-205`
**Issue:** `_load_schema_class` returns `getattr(mod, class_name)` after verifying the attribute exists, but does not verify that the returned object is a Pydantic `BaseModel` subclass. If a skill's schema file defines a class with the expected name that is not a `BaseModel` (e.g. a plain dataclass or function), `_parse_llm_response` will call `output_schema_class.model_validate(...)` and raise an `AttributeError`, not a `SkillMalformedError`. This makes the failure message confusing and bypasses the structured exception hierarchy.

**Fix:**
```python
from pydantic import BaseModel as PydanticBaseModel

# In _load_schema_class, after the getattr:
try:
    cls = getattr(mod, class_name)
except AttributeError:
    raise SkillMalformedError(
        skill_name, f"{schema_file} is missing expected class {class_name!r}"
    )
if not (isinstance(cls, type) and issubclass(cls, PydanticBaseModel)):
    raise SkillMalformedError(
        skill_name,
        f"{schema_file}: {class_name!r} must be a Pydantic BaseModel subclass"
    )
return cls
```

---

### WR-03: LLM confidence value accepted without range validation

**File:** `backend/app/infrastructure/skills/loader.py:278`
**Issue:** `confidence = float(data.get("confidence", 0.0))` converts the raw LLM value but does not clamp or validate the result to `[0.0, 1.0]`. The docstring and `_ENVELOPE_INSTRUCTIONS` both state "a number between 0.0 and 1.0", but an adversarial or hallucinating LLM could return `999` or `-1`. Callers that branch on `result.confidence > 0.8` would then behave unpredictably. The fix is a simple clamp; raising `SkillMalformedError` is also acceptable if strict enforcement is desired.

**Fix:**
```python
# Replace line 278:
raw_confidence = float(data.get("confidence", 0.0))
confidence = max(0.0, min(1.0, raw_confidence))
```

---

## Info

### IN-01: `input_data.model_dump()` will raise AttributeError for non-Pydantic, non-dict input

**File:** `backend/app/infrastructure/skills/loader.py:105`
**Issue:** In `SkillRunner.run()`, the `else` branch calls `input_data.model_dump()` for any value that is not a `dict`. Plain Python dataclasses, `NamedTuple`, or other objects without a `model_dump()` method will raise `AttributeError` with no diagnostic message. The method signature says `input_data: Any` and the docstring says "dict or Pydantic model instance", but that contract is unenforced.

**Fix:** Add an explicit branch or guard:
```python
if isinstance(input_data, dict):
    user_content = json.dumps(input_data, ensure_ascii=False)
elif hasattr(input_data, "model_dump"):
    user_content = json.dumps(input_data.model_dump(), ensure_ascii=False)
else:
    raise TypeError(
        f"SkillRunner.run() input_data must be a dict or Pydantic model, "
        f"got {type(input_data).__name__!r}"
    )
```

---

### IN-02: Front-matter dict returned but never consumed or validated

**File:** `backend/app/infrastructure/skills/loader.py:154, 208-231`
**Issue:** `_parse_skill_md` returns a `tuple[dict[str, str], str]` (front-matter, system-prompt). `load_skill()` discards the front-matter with `_`. The front-matter is parsed but its `name` key (which could be validated against the directory name) and other fields are never checked. The bare `split(":", 1)` parsing on line 229 is also fragile — any line containing `:` (including comment lines) is silently added to `fm` as a key-value pair.

**Fix (optional for current phase):** Either remove the front-matter parsing entirely (since it is unused), or keep it and validate at minimum that `fm.get("name") == skill_name`. The split logic should also guard against lines that are not `key: value` pairs:
```python
for line in lines[1:fm_end]:
    if ":" in line and not line.lstrip().startswith("#"):
        k, v = line.split(":", 1)
        fm[k.strip()] = v.strip()
```

---

### IN-03: Redundant `.suffix != ".py"` check in `_load_schema_class`

**File:** `backend/app/infrastructure/skills/loader.py:187`
**Issue:** Line 187 checks `file_path.suffix != ".py"` but `schema_file` is always one of the two hardcoded string literals `"input_schema.py"` or `"output_schema.py"`. The suffix can never be anything other than `.py`. The check is dead code and creates a misleading impression that non-`.py` files might reach this path.

**Fix:** Remove the suffix check; the path-existence check alone is sufficient:
```python
if not file_path.exists():
    raise SkillMalformedError(skill_name, f"missing {schema_file}")
```

---

### IN-04: Integration tests rely on real on-disk skill directory without fixture isolation

**File:** `backend/tests/test_skill_loader.py:77-79, 182-198`
**Issue:** `test_load_skill_returns_runner` and `test_skill_runner_run_returns_result` call `load_skill("cross-channel-dedup")` against the real `backend/skills/cross-channel-dedup/` directory rather than a `tmp_path`-isolated copy. If the skill schema evolves (e.g. required fields are added to `CrossChannelDedupOutput`), the second test's `valid_response = json.dumps({"output": {}, ...})` payload will fail schema validation and break the test with a `SkillMalformedError` instead of a clear assertion error. This also makes the tests implicitly order-dependent on the skill file being present.

**Fix:** Either accept this as intentional (these function as light integration tests) and add a comment explaining the dependency, or isolate them with `tmp_path` + `patch.object(_SKILLS_ROOT)` consistent with the other tests.

---

_Reviewed: 2026-04-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
