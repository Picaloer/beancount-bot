# Iteration Log — 2026-03-30 · LLM Prompt Enrichment & Rule Feedback Optimizer

## Overview

This iteration delivers two interconnected improvements to the classification system:

1. **Richer LLM classification prompt** — the model now receives the full current ruleset as context, dramatically reducing "other/uncategorised" misses for well-known merchants.
2. **Rule feedback optimizer** — a user-confirmed loop that turns classification signals (manual corrections, repeated high-confidence LLM outputs) into candidate rules, which the user reviews before they become permanent.

---

## What Changed

### Backend — Classification Agent (`classification_agent.py`)

- Removed bare taxonomy-only prompt; replaced with a structured prompt that includes:
  - The full `category_tree` taxonomy
  - Current **user-defined rules** (up to 20) and **system rules** (up to 40) as "rule knowledge" context
  - Stronger classification principles: prefer semantic inference, avoid "其他/未分类", special-case transfers and digital services
  - Explicit confidence band definitions (0.9–1.0 very certain, etc.)
- Added `direction` and `source` fields to per-transaction LLM input payloads
- `ClassificationAgent.__init__` now accepts `user_rules: list[Rule]` and passes them into the prompt
- Removed unused `AgentResult` import

### Backend — Import Pipeline (`import_tasks.py`)

- `update_transaction_category` now called with `confidence=result.confidence` so every import persists the LLM's confidence score
- `ClassificationAgent` constructed with the loaded `user_rules` so the prompt reflects the user's actual ruleset at import time

### Backend — Repository (`transaction_repo.py`)

- `update_transaction_category`: new optional `confidence` param, persisted to `category_confidence` column
- `save_rule_suggestion`: create or upsert a pending suggestion; deduplication by `(user_id, match_field, match_value, category_l1, category_l2, status=pending)`; raises `ValueError` if `match_value` is empty
- `list_rule_suggestions`: filter by `user_id` and `status`
- `approve_rule_suggestion`: promote pending suggestion → active `CategoryRuleORM`; idempotent on the rule (doesn't duplicate); marks suggestion `approved`
- `reject_rule_suggestion`: marks suggestion `rejected`
- `generate_rule_suggestions_from_history`: scan all LLM/manual transactions; group by `(merchant, category_l1, category_l2)`; produce suggestions for:
  - Any merchant with ≥1 **manual** correction
  - Any merchant with ≥2 **LLM** classifications at confidence ≥ 0.85
  - Skip merchants that already have an active rule

### Backend — Categories API (`categories.py`)

New endpoints added to the existing `/api/v1/categories` router:

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/rule-suggestions` | List suggestions (filter by `?status=pending|approved|rejected`) |
| `POST` | `/rule-suggestions` | Create a suggestion manually |
| `POST` | `/rule-suggestions/generate` | Generate suggestions from transaction history |
| `POST` | `/rule-suggestions/{id}/approve` | Approve → becomes active rule |
| `POST` | `/rule-suggestions/{id}/reject` | Reject suggestion |

- Fixed `sample_transactions: list[dict] = Field(default_factory=list)` (removed mutable default)

### Backend — Transactions API (`transactions.py`)

- `PATCH /{id}/category` now:
  - Validates `category_l1` / `category_l2` against the taxonomy
  - Persists confidence `1.0` for manual overrides
  - Auto-creates a `manual_feedback` pending suggestion when the transaction has a non-empty merchant
- `_serialize` now includes `category_confidence` field in transaction list responses

### Backend — Database (`database.py`)

- `_build_engine()` helper: auto-detects SQLite (for tests) vs Postgres; skips incompatible `pool_size`/`max_overflow` args on SQLite

### Database Migration (`004_add_rule_suggestions.py`)

- `ALTER TABLE transactions ADD COLUMN category_confidence NUMERIC(4,3) DEFAULT 0`
- `CREATE TABLE rule_suggestions (id, user_id, match_field, match_value, category_l1, category_l2, confidence, source, status, reason, evidence_count, sample_transactions, created_at, resolved_at)`
- Index on `(user_id, status, created_at)` for efficient listing

### Parser — CMB PDF (`cmb.py`)

- Lazy-import `RapidOCR` inside `_extract_pdf_text_via_ocr` so a missing `libxcb.so.1` in the Docker container doesn't crash the whole app at import time (OCR fallback raises a clear `RuntimeError` only when actually needed)

### Tests (`tests/`)

- Added `tests/conftest.py` — sets `DATABASE_URL=sqlite:///:memory:` before any app import; ensures test isolation from production Postgres
- Added `tests/test_category_suggestions.py` — **20 tests** covering:
  - Category tree endpoint
  - Rule CRUD (create, list, delete, validation)
  - Suggestion CRUD (create, deduplication, invalid category)
  - Approve workflow (creates rule, idempotency, 400 on second approve)
  - Reject workflow (status change, 404 on missing)
  - Generate from history (LLM high-confidence, skip low-confidence, manual always included, skip existing rules)
  - Manual category update → auto-suggestion, no suggestion for empty merchant

---

## Test Results

```
23 passed (20 new + 3 parser regression), 0 failed
```

## Live Regression

- Rebuilt Docker images, applied migration 004 to production Postgres
- `/api/v1/categories/rule-suggestions` — returns `[]` correctly on fresh state
- `/api/v1/categories/rule-suggestions/generate` — surfaced real historical manual correction ("南京大牌档 → 餐饮・堂食") as a pending suggestion
- Approve endpoint — promoted the suggestion to an active `category_rules` row, confirmed via `/api/v1/categories/rules`
- All existing import/classification/report endpoints unaffected

---

## Design Decisions

- **User confirmation is mandatory** — suggestions are never auto-promoted. The user must explicitly call `/approve` or `/reject`. This was the explicit product requirement.
- **Two evidence sources for suggestions**: manual corrections (highest signal, threshold = 1) and repeated high-confidence LLM outputs (threshold: ≥2 occurrences at ≥0.85 confidence).
- **Deduplication** — re-submitting the same suggestion updates confidence rather than creating a duplicate.
- **Existing-rule guard** — `generate` skips merchants that already have an active rule, preventing noise.
- **Lazy OCR import** — isolates the `libxcb` dependency so the core API stays healthy in environments without X11 libs.
