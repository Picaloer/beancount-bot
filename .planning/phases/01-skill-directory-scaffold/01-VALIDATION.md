---
phase: 1
slug: skill-directory-scaffold
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 (installed in backend venv) |
| **Config file** | None — no `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml` |
| **Quick run command** | `cd backend && uv run pytest tests/test_skill_scaffold.py -v` |
| **Full suite command** | `cd backend && uv run pytest tests/ -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/test_skill_scaffold.py -v`
- **After every plan wave:** Run `cd backend && uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | SKILL-01 | — | N/A | unit | `uv run pytest tests/test_skill_scaffold.py -v` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | SKILL-01 | — | N/A | unit | `uv run pytest tests/test_skill_scaffold.py::test_skills_directory_exists -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | SKILL-01 | — | N/A | unit | `uv run pytest tests/test_skill_scaffold.py::test_skill_subdirectory_exists -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | SKILL-01 | — | N/A | unit | `uv run pytest tests/test_skill_scaffold.py::test_skill_md_has_yaml_frontmatter -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | SKILL-01 | — | N/A | unit | `uv run pytest tests/test_skill_scaffold.py::test_skill_md_has_required_sections -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | SKILL-01 | — | N/A | unit | `uv run pytest tests/test_skill_scaffold.py::test_input_schema_importable -x` | ❌ W0 | ⬜ pending |
| 1-01-07 | 01 | 1 | SKILL-01 | — | N/A | unit | `uv run pytest tests/test_skill_scaffold.py::test_output_schema_importable -x` | ❌ W0 | ⬜ pending |
| 1-01-08 | 01 | 1 | SKILL-01 | — | N/A | unit | `uv run pytest tests/test_skill_scaffold.py::test_schema_files_no_app_imports -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_skill_scaffold.py` — stubs for all SKILL-01 structural assertions (full test code provided in RESEARCH.md `Code Examples` section)

*Wave 0 must complete before Wave 1 tasks touch the skills directory.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `backend/skills/README.md` exists and documents naming + file conventions | SC-3 | README content is subjective; presence check is automated via `ls backend/skills/README.md` | Run `ls backend/skills/README.md` — must return file path with exit code 0 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
