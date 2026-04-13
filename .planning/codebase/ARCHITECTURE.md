# Architecture
_Last updated: 2026-04-13_

## Summary

Beancount Bot is a full-stack, AI-powered personal finance system. The backend is a Python FastAPI service backed by PostgreSQL + Redis, processing bill imports asynchronously via Celery workers. The frontend is a Next.js 16 App Router SPA that polls the backend REST API. The core pipeline transforms raw bill CSVs/PDFs into classified Beancount double-entry journal entries using a four-stage Chain-of-Responsibility classifier augmented by an LLM.

---

## High-Level Component Diagram

```
Browser (Next.js 16, port 3000)
  └─ lib/api.ts  ──────────── HTTP/JSON ──────────────┐
                                                       ▼
                                            FastAPI App (port 8000)
                                            app/api/v1/*.py
                                                       │
                                    ┌──────────────────┼──────────────────┐
                                    ▼                  ▼                  ▼
                            Application           Domain Layer       Infrastructure
                            Services              (pure Python)      (framework/I-O)
                            app/application/      app/domain/        app/infrastructure/
                                    │
                                    ├─── import_service.py
                                    │       └─ enqueues Celery task →─┐
                                    │                                  ▼
                                    │                        Celery Worker (same image)
                                    │                        queue/import_tasks.py
                                    │                                  │
                                    │       ┌──────────────────────────┤
                                    │       ▼                          │
                                    │   parsers/registry.py            │
                                    │   (wechat, alipay, cmb)         │
                                    │                                  │
                                    │   domain/classification/         │
                                    │   pipeline.py  ◄─────────────────┘
                                    │     Stage 1: user_rules
                                    │     Stage 2: system_rules (~500 keywords)
                                    │     Stage 3: LLM (Claude / DeepSeek)
                                    │     Stage 4: fallback
                                    │
                                    └─── report_service.py
                                          └─ InsightAgent → LLM

PostgreSQL ←─ SQLAlchemy ORM ─── persistence/
Redis      ←─ Celery broker/backend ── queue/celery_app.py
```

---

## Layers

### API Layer
- Purpose: Receive HTTP requests, validate inputs, delegate to application services, serialize responses.
- Location: `backend/app/api/v1/`
- Contains: Seven FastAPI `APIRouter` modules (`bills.py`, `transactions.py`, `reports.py`, `categories.py`, `budgets.py`, `settings.py`, `query.py`).
- Depends on: `app/application/` services, `app/infrastructure/persistence/database.py` (session DI), `app/core/config.py`.
- Pattern: Pydantic request/response models defined inline; no business logic in routers.

### Application Layer
- Purpose: Orchestrate multi-step business workflows; own no persistence primitives.
- Location: `backend/app/application/`
- Contains: `import_service.py`, `report_service.py`, `budget_service.py`, `runtime_settings_service.py`, `query_service.py`.
- Depends on: `app/infrastructure/persistence/repositories/transaction_repo.py`, `app/infrastructure/ai/`, `app/infrastructure/queue/import_tasks.py`.
- Key design: `import_service.submit_import()` saves the file to disk and enqueues a Celery task — it never processes data itself.

### Domain Layer
- Purpose: Pure business logic with zero framework/ORM dependencies.
- Location: `backend/app/domain/`
- Sub-packages:
  - `transaction/models.py` — `RawTransaction`, `Transaction`, `BillSource`, `TransactionDirection`, `CategorySource`, `build_transaction_dedupe_key()`.
  - `classification/pipeline.py` — `ClassificationPipeline` (Chain of Responsibility): `UserDefinedRuleStage → SystemRuleStage → LLMStage → FallbackStage`.
  - `classification/batch_runner.py` — concurrent batch runner with `BatchProgressUpdate` callbacks.
  - `classification/rule_engine.py` — `RuleEngine` with 500+ `SYSTEM_RULES`.
  - `classification/category_tree.py` — authoritative two-level `CATEGORY_TREE` dict used in prompts and validation.
  - `beancount/engine.py` — `BeancountEngine.generate_entry()` converts `Transaction → BeancountEntry` text; no external beancount library.
  - `beancount/account_resolver.py` — maps categories to Beancount account strings.

### Infrastructure Layer
- Purpose: Adapters for all external systems.
- Location: `backend/app/infrastructure/`
- Sub-packages:
  - `parsers/` — pluggable parser adapters (`wechat.py`, `alipay.py`, `cmb.py`) registered via `registry.py`.
  - `ai/` — `LLMAdapter` protocol, `ClaudeClient`, `DeepSeekClient`, `create_llm_client()` factory, `ClassificationAgent`, `InsightAgent`, `AgentRegistry`.
  - `persistence/` — SQLAlchemy engine/session (`database.py`), all ORM models (`orm_models.py`), single repository (`transaction_repo.py`).
  - `queue/` — `celery_app.py` configuration, `import_tasks.py` with `process_bill_import` task and `resume_import_after_duplicate_review`.

### Core
- Purpose: Cross-cutting concerns.
- Location: `backend/app/core/`
- Contains: `config.py` (pydantic-settings `Settings` singleton), `exceptions.py`, `event_bus.py` (in-memory EventBus), `logging.py`, `timezone.py`.

---

## Import Pipeline (Primary Data Flow)

```
POST /api/v1/bills/import
        │
        ▼
import_service.submit_import()
  1. Write file bytes to /uploads/{import_id}_{filename}
  2. parser_registry.auto_detect_file() → identify format
  3. repo.create_import() → INSERT bill_imports + import_stages + import_summaries
  4. process_bill_import.delay() → enqueue Celery task on "imports" queue
  5. Return {import_id, status:"pending"}
        │
        ▼ (async, Celery worker)
process_bill_import(import_id, file_path, user_id)
  Stage 1 — PARSE
    parser_registry.parse_file(file_path) → list[RawTransaction]
    update import_stages.parse → done

  Stage 2 — DEDUPE
    repo.bulk_create_transactions() — upsert with external_id + dedupe_key unique constraints
    repo.create_duplicate_review_groups() — detect cross-source near-duplicates

  Stage 3 — DUPLICATE REVIEW (optional pause)
    If duplicate groups found:
      update status="reviewing_duplicates"; return and wait
      Frontend polls GET /bills/import/{id} every 2 s
      User resolves each group via POST .../duplicate-review/{group_id}/resolve
      After last group resolved: resume_import_after_duplicate_review() continues

  Stage 4 — CLASSIFY
    _build_pipeline() → ClassificationPipeline + ClassificationAgent
    classify_transactions() batch-runs pipeline with concurrency
    Progress callbacks update import status rows in real time

  Stage 5 — BEANCOUNT
    BeancountEngine.generate_entry() per transaction
    repo.save_beancount_entry() → INSERT beancount_entries

  Final: update status="done", update import_summaries
```

Frontend polls `GET /api/v1/bills/import/{importId}` every 2 seconds via SWR until `status` is terminal (`done` | `failed`).

---

## Classification Pipeline (Chain of Responsibility)

```
RawTransaction
      │
      ▼
UserDefinedRuleStage   ← DB-loaded user CategoryRuleORM rows (priority desc)
      │ None (pass)
      ▼
SystemRuleStage        ← ~500 hard-coded SYSTEM_RULES (rule_engine.py)
      │ None (pass)
      ▼
LLMStage               ← ClassificationAgent.classify_batch()
      │                   (batches of up to llm_batch_size txns → Claude/DeepSeek)
      │ None (pass)
      ▼
FallbackStage          ← returns ClassificationResult("其他", "未分类", 0.0)
      │
      ▼
ClassificationResult(category_l1, category_l2, confidence, source)
```

`classify_before_llm()` short-circuits at LLMStage to determine which transactions need LLM, used to compute `llm_total_batches` upfront.

---

## Deduplication Strategy

Two complementary keys per `TransactionORM`:
- `external_id` — platform-native order number (`交易单号` / `交易订单号`); unique constraint `(user_id, external_id)`.
- `dedupe_key` — SHA-256 hash of `direction|amount|currency|merchant|description|timestamp`; unique constraint `(user_id, dedupe_key)`.

`bulk_create_transactions()` attempts INSERT for each row, catches `IntegrityError` for both constraints, and returns only successfully inserted rows.

Cross-source near-duplicate detection groups transactions by `(date, amount, currency)` across different sources and creates `DuplicateReviewGroupORM` records requiring human resolution.

---

## API Routes

| Method | Path | Router | Purpose |
|--------|------|--------|---------|
| POST | `/api/v1/bills/import` | bills.py | Upload bill file; start async import |
| GET | `/api/v1/bills/import/{id}` | bills.py | Poll import status |
| GET | `/api/v1/bills/import/{id}/detail` | bills.py | Rich import detail with stages |
| POST | `/api/v1/bills/import/{id}/duplicate-review/{gid}/resolve` | bills.py | Resolve one duplicate group |
| DELETE | `/api/v1/bills/import/{id}` | bills.py | Delete import and all child data |
| GET | `/api/v1/bills/imports` | bills.py | List last 20 imports |
| GET | `/api/v1/transactions` | transactions.py | List transactions (filter + paginate) |
| PATCH | `/api/v1/transactions/{id}/category` | transactions.py | Manual category override |
| GET | `/api/v1/transactions/summary` | transactions.py | Total expense/income aggregates |
| GET | `/api/v1/reports/monthly/{YYYY-MM}` | reports.py | Monthly report with AI insight |
| GET | `/api/v1/reports/months` | reports.py | Available months with data |
| GET | `/api/v1/reports/ranking/merchants` | reports.py | Top merchants by spend |
| GET | `/api/v1/reports/trends/categories/{YYYY-MM}` | reports.py | Category spend trends |
| GET | `/api/v1/reports/beancount/{YYYY-MM}` | reports.py | Export Beancount journal text |
| GET | `/api/v1/categories` | categories.py | Two-level category tree |
| GET/POST/DELETE | `/api/v1/categories/rules` | categories.py | CRUD user classification rules |
| GET/POST | `/api/v1/categories/rule-suggestions` | categories.py | LLM-generated rule candidates |
| POST | `/api/v1/categories/rule-suggestions/generate` | categories.py | Trigger suggestion generation |
| POST | `/api/v1/categories/rule-suggestions/{id}/approve` | categories.py | Approve suggestion → create rule |
| POST | `/api/v1/categories/rule-suggestions/{id}/reject` | categories.py | Reject suggestion |
| GET | `/api/v1/budgets/{YYYY-MM}` | budgets.py | Get or generate budget plan |
| GET | `/api/v1/settings/runtime` | settings.py | Read LLM runtime config |
| PUT | `/api/v1/settings/runtime` | settings.py | Update LLM runtime config |
| POST | `/api/v1/query` | query.py | Answer natural-language finance question |
| GET | `/health` | main.py | Health check |

---

## Database Schema (ORM Models)

All ORM models defined in `backend/app/infrastructure/persistence/models/orm_models.py`:

| Table | Key Columns | Relationships |
|-------|-------------|---------------|
| `users` | `id`, `email` | → imports, transactions, category_rules, budget_plans, duplicate_review_groups |
| `bill_imports` | `id`, `user_id`, `source`, `status`, `stage_message`, LLM token counts | → transactions, stages, summary, duplicate_review_groups |
| `import_stages` | `import_id`, `stage_key` (parse/dedupe/duplicate_review/classify/beancount), `status`, `message` | → bill_imports |
| `import_summaries` | `import_id`, counts (inserted, duplicate, rule/llm/fallback) | 1:1 → bill_imports |
| `transactions` | `id`, `user_id`, `import_id`, `source`, `direction`, `amount`, `merchant`, `category_l1/l2`, `external_id`, `dedupe_key`, `duplicate_review_status` | → beancount_entry, duplicate_review_group |
| `duplicate_review_groups` | `id`, `import_id`, `review_status`, `ai_suggestion`, candidate amounts | → transactions |
| `beancount_entries` | `transaction_id`, `entry_date`, `raw_beancount`, `postings` JSON | 1:1 → transactions |
| `category_rules` | `user_id`, `match_field`, `match_value`, `category_l1/l2`, `priority` | → users |
| `rule_suggestions` | `user_id`, `status` (pending/approved/rejected), `confidence`, `sample_transactions` JSON | |
| `monthly_reports` | `user_id`, `year_month`, `data` JSON, `ai_insight` | |
| `budget_plans` | `user_id`, `year_month`, `category_l1`, `amount`, `spent`, `usage_ratio` | → users |
| `runtime_settings` | `user_id`, `llm_provider`, `llm_model`, API keys, batch/concurrency params | 1:1 per user |

Migrations: `backend/alembic/versions/` (001–008, sequential).

---

## State Management

**Backend:** No in-process state. Import lifecycle state is persisted entirely in `bill_imports.status` and `import_stages` rows. The Celery worker reads/writes these rows to communicate progress to the API layer.

**Frontend:** SWR (stale-while-revalidate) for all server state. No Redux or global client store. Polling intervals are dynamic: active imports poll every 2 seconds; terminal-status imports stop polling. All API interactions go through `frontend/lib/api.ts`.

---

## Key Architectural Patterns

| Pattern | Where |
|---------|-------|
| Chain of Responsibility | `ClassificationPipeline` (4 stages) |
| Adapter + Registry | `parsers/registry.py` — parser plugins self-register in `parsers/__init__.py` |
| Repository | `transaction_repo.py` — single repo for all DB operations |
| Application Service | `application/*.py` — orchestrate domain + infra, no HTTP concerns |
| Factory | `ai/factory.py` — `create_llm_client()` selects Claude vs DeepSeek |
| Domain Model separation | `domain/transaction/models.py` (pure) vs `orm_models.py` (SQLAlchemy) |
| Async task queue | Celery + Redis for the heavy import pipeline |
| Event Bus | `core/event_bus.py` — in-memory, synchronous; defined for future async migration |
| Single-user MVP | `DEFAULT_USER_ID` constant; no auth middleware |

---

## Error Handling

- Parse errors → `ParseError` / `UnsupportedFormatError` in `core/exceptions.py` → HTTP 422.
- Import not found → `ImportNotFoundError` → HTTP 404.
- Celery task failures → logged, `bill_imports.status = "failed"`, all stages set to `"failed"`, task retried up to 3 times with 30 s delay.
- LLM errors → caught in `_build_pipeline()`; if LLM unavailable, pipeline falls through to FallbackStage.
- Beancount entry generation failures → logged as warning, entry skipped; import continues.
- `EventBus` handler errors → logged, not re-raised.

---

## LLM Integration

- Default: `claude-haiku-4-5-20251001` via `anthropic` SDK (`ClaudeClient`).
- Alternate: DeepSeek via OpenAI-compatible endpoint (`DeepSeekClient` using `openai` SDK).
- Runtime switching: `PUT /api/v1/settings/runtime` writes to `runtime_settings` table; next import picks up new config.
- Classification batches: up to `llm_batch_size` (default 20) transactions per API call; up to `llm_max_concurrency` (default 4) concurrent calls.
- Monthly insight: `InsightAgent` runs synchronously inside `report_service.get_or_generate_report()`.

---

## Deployment

All services containerized via `docker-compose.yml`:

```
postgres:16-alpine      → volume postgres_data
redis:7-alpine          → volume redis_data
migrate (one-off)       → alembic upgrade head
backend (FastAPI)       → port 8000, volume uploads
worker (Celery)         → queue "imports", concurrency 2, volume uploads
frontend (Next.js)      → port 3000, standalone output
```

`ANTHROPIC_API_KEY` (or `DEEPSEEK_API_KEY`) injected from root `.env`. Frontend `NEXT_PUBLIC_API_URL` is a build-arg defaulting to `http://localhost:8000/api/v1`.

---

## Gaps & Unknowns

- `core/event_bus.py` defines `TransactionImported`, `TransactionClassified`, `MonthlyReportRequested` events but no handlers are subscribed; the bus is unused in the current implementation.
- `AgentRegistry` in `infrastructure/ai/agents/registry.py` exists but is not wired into production code.
- The `query_service.py` uses pattern-matching intent detection (no LLM) — it cannot handle free-form questions beyond a fixed set of intents.
- `budget_service._build_budget_recommendations()` is purely statistical (mean + peak buffer); it is labeled "ai" in the source field but does not call an LLM.
- No authentication or per-user isolation beyond the hardcoded `DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"`.
- No test coverage for the Celery task flow end-to-end; tests in `backend/tests/` cover parser and deduplication only.
