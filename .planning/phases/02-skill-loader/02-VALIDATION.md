---
phase: 2
slug: skill-loader
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `backend/pyproject.toml` (no `[tool.pytest.ini_options]` — defaults only) |
| **Quick run command** | `uv run pytest tests/test_skill_loader.py -v` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_skill_loader.py -v`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | SKILL-02 | T-02-01 | Skill name validated: only `[a-z0-9-]+` allowed before path construction | unit | `uv run pytest tests/test_skill_loader.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | SKILL-02 | — | `load_skill("cross-channel-dedup")` returns a `SkillRunner` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_returns_runner -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | SKILL-02 | — | New skill directory discoverable without loader code changes | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_discovery_no_code_changes -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | SKILL-02 | — | Missing skill dir raises `SkillNotFoundError` with skill name | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_not_found -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | SKILL-02 | — | Missing `SKILL.md` raises `SkillMalformedError` with skill name | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_missing_skill_md -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 1 | SKILL-02 | — | Missing `input_schema.py` raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_missing_input_schema -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 1 | SKILL-02 | — | Missing `output_schema.py` raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_missing_output_schema -x` | ❌ W0 | ⬜ pending |
| 02-01-08 | 01 | 1 | SKILL-02 | — | Schema class missing from file raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_load_skill_missing_class -x` | ❌ W0 | ⬜ pending |
| 02-01-09 | 01 | 1 | SKILL-02 | — | `SkillRunner.run()` returns `SkillResult` with `structured_output`, `reasoning`, `confidence` | unit | `uv run pytest tests/test_skill_loader.py::test_skill_runner_run_returns_result -x` | ❌ W0 | ⬜ pending |
| 02-01-10 | 01 | 1 | SKILL-02 | T-02-01 | Invalid LLM JSON raises `SkillMalformedError` (not silently accepted) | unit | `uv run pytest tests/test_skill_loader.py::test_skill_runner_invalid_json -x` | ❌ W0 | ⬜ pending |
| 02-01-11 | 01 | 1 | SKILL-02 | T-02-01 | LLM output failing schema validation raises `SkillMalformedError` | unit | `uv run pytest tests/test_skill_loader.py::test_skill_runner_schema_validation_failure -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_skill_loader.py` — stubs for SKILL-02 (11 test cases listed above)
- [ ] `backend/app/infrastructure/skills/__init__.py` — empty package marker
- [ ] `backend/app/infrastructure/skills/loader.py` — implementation stub (empty `load_skill()` so imports resolve)

*No framework or shared fixture gaps — `conftest.py` from Phase 1 already handles `sys.path` and env setup correctly.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `SkillRunner.run()` calls the real LLM and returns a populated `SkillResult` | SKILL-02 | Requires live LLM API key; cost is non-trivial for CI | `uv run python -c "from app.infrastructure.skills.loader import load_skill; from app.infrastructure.ai.factory import create_llm_client; r = load_skill('cross-channel-dedup'); res = r.run(create_llm_client(), {}); print(res)"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
