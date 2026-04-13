---
phase: 01-skill-directory-scaffold
reviewed: 2026-04-13T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - backend/tests/test_skill_scaffold.py
  - backend/skills/README.md
  - backend/skills/cross-channel-dedup/SKILL.md
  - backend/skills/cross-channel-dedup/input_schema.py
  - backend/skills/cross-channel-dedup/output_schema.py
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-13T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Five files were reviewed: the scaffold test suite, the skills directory README, the `cross-channel-dedup` SKILL.md, and the two placeholder schema files. The structure is sound and all required sections/files are in place for Phase 1. One warning-level issue was found in the test suite (a latent crash path that produces an opaque `AttributeError` rather than a useful test failure). Two info-level items cover a documentation inconsistency in the schema docstrings and a minor test organization gap.

## Warnings

### WR-01: `spec.loader` is not guarded before use in importability tests

**File:** `backend/tests/test_skill_scaffold.py:48` (also line 56)

**Issue:** `importlib.util.spec_from_file_location()` can return `None` when the path does not resolve (e.g., the file is deleted between the existence check and the import test, or a custom finder returns `None`). The subsequent `importlib.util.module_from_spec(spec)` call on line 48 would then raise `AttributeError: 'NoneType' object has no attribute ...` rather than producing a clean test failure. Even when a spec is returned, `spec.loader` itself can be `None` for namespace packages, causing `spec.loader.exec_module(mod)` on line 49 to crash with the same opaque error. Because the existence tests (`test_input_schema_exists`, `test_output_schema_exists`) are independent functions, pytest does not guarantee they run before the importability tests when tests are filtered or re-ordered.

**Fix:**
```python
def test_input_schema_importable():
    schema_path = SKILLS_DIR / SKILL_NAME / "input_schema.py"
    spec = importlib.util.spec_from_file_location("input_schema", schema_path)
    assert spec is not None, f"Could not create module spec for {schema_path}"
    assert spec.loader is not None, f"Module spec has no loader for {schema_path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "CrossChannelDedupInput")
```

Apply the same guard pattern to `test_output_schema_importable` (lines 53-60).

## Info

### IN-01: Schema docstrings reference a Python import path that requires hyphen-to-underscore conversion

**File:** `backend/skills/cross-channel-dedup/input_schema.py:5` and `backend/skills/cross-channel-dedup/output_schema.py:5`

**Issue:** The module docstrings state:
```
from skills.cross_channel_dedup.input_schema import CrossChannelDedupInput
```
The directory on disk is `cross-channel-dedup` (with hyphens). Python cannot import a package named with hyphens via the normal import machinery — the loader must convert hyphens to underscores before the path is importable as `skills.cross_channel_dedup`. The docstring makes an implicit assumption about the future Phase 2 loader's behavior (hyphen → underscore translation). If the loader does not perform this translation, the documented import will fail at runtime. This is a documentation inconsistency that could mislead the Phase 2 implementer.

**Fix:** Either clarify the docstring to make the assumption explicit, or note that the loader is responsible for the name conversion:
```python
"""
Input schema for the cross-channel-dedup skill.

Loaded by the Phase 2 skill loader, which converts the directory name
'cross-channel-dedup' to the Python package name 'cross_channel_dedup':
    from skills.cross_channel_dedup.input_schema import CrossChannelDedupInput
"""
```

### IN-02: Test functions have no `pytest.mark` categorization

**File:** `backend/tests/test_skill_scaffold.py:9-67`

**Issue:** The project convention (from `backend/tests/`) uses `pytest.mark` for test categorization (`unit`, `integration`). These scaffold tests are pure filesystem and importability checks with no external dependencies — they should be marked `@pytest.mark.unit` for consistency and to allow selective test runs.

**Fix:** Add `@pytest.mark.unit` to each test function, e.g.:
```python
@pytest.mark.unit
def test_skills_directory_exists():
    assert SKILLS_DIR.is_dir(), f"backend/skills/ not found at {SKILLS_DIR}"
```

---

_Reviewed: 2026-04-13T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
