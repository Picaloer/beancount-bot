---
phase: 3
slug: skill-result-contract
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && uv run pytest tests/test_skill_loader.py -v` |
| **Full suite command** | `cd backend && uv run pytest -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest tests/test_skill_loader.py -v`
- **After every plan wave:** Run `cd backend && uv run pytest -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 1 | SKILL-03 | — | N/A | unit | `uv run pytest tests/test_skill_loader.py -k "envelope" -v` | ❌ Wave 0 | ⬜ pending |
| 3-01-02 | 01 | 1 | SKILL-03 | — | N/A | unit | `uv run pytest tests/test_skill_loader.py -k "public_api" -v` | ❌ Wave 0 | ⬜ pending |
| 3-01-03 | 01 | 1 | SKILL-03 | — | N/A | regression | `uv run pytest tests/test_skill_loader.py -v` | ✅ Exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_skill_loader.py` — add parametrized `test_skill_runner_envelope_contract_violations` block (8 rejection scenarios: D-01 missing keys ×3, D-02 empty/whitespace reasoning ×2, D-03 out-of-range/non-numeric confidence ×3)
- [ ] `backend/tests/test_skill_loader.py` — add `test_public_api_imports` to verify `from app.infrastructure.skills import SkillResult, SkillRunner, load_skill, SkillNotFoundError, SkillMalformedError` works

*Existing test infrastructure (pytest, MockLLMClient, in-memory SkillRunner) is already in place. Only new test cases need to be added to the existing file.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
