# Codebase Structure
_Last updated: 2026-04-13_

## Summary

The repository is a monorepo with three top-level directories: `backend/` (Python/FastAPI), `frontend/` (Next.js 16), and `docs/`. All orchestration is done via Docker Compose; no shared build tooling couples the two apps. The backend follows a strict four-layer architecture (api → application → domain → infrastructure). The frontend is a flat Next.js App Router project with all pages under `app/` and a single API client module at `lib/api.ts`.

---

## Directory Layout

```
beancount-bot/
├── .env.example              # Required env var template (copy to .env)
├── .gitignore
├── CLAUDE.md                 # Project-specific dev rules (branch naming, etc.)
├── Makefile                  # Docker Compose shortcuts (setup, up, down, logs, shell-*)
├── docker-compose.yml        # 5-service stack: postgres, redis, migrate, backend, worker, frontend
├── docs/                     # Architecture diagrams and product docs (markdown + PNG)
│
├── backend/                  # Python 3.13 FastAPI application
│   ├── pyproject.toml        # uv-managed dependencies
│   ├── main.py               # Stub (unused entry); real entry is app/main.py
│   ├── alembic.ini
│   ├── Dockerfile
│   ├── entrypoint.sh         # Wait for DB, then uvicorn
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/         # 8 sequential migration files (001–008)
│   ├── app/
│   │   ├── main.py           # FastAPI app factory, CORS, router registration, lifespan
│   │   ├── core/             # Cross-cutting concerns
│   │   ├── domain/           # Pure business logic
│   │   ├── application/      # Business service orchestrators
│   │   ├── infrastructure/   # Framework adapters (DB, queue, AI, parsers)
│   │   └── api/v1/           # HTTP routers
│   ├── tests/
│   └── uploads/              # Runtime upload directory (shared with worker via Docker volume)
│
└── frontend/                 # Next.js 16 App Router application
    ├── package.json           # pnpm workspace
    ├── tsconfig.json          # strict TS, path alias @/* → ./
    ├── app/
    │   ├── layout.tsx         # Root layout: Sidebar + main content wrapper
    │   ├── globals.css        # CSS custom properties (gold/dark palette)
    │   ├── page.tsx           # Dashboard (/)
    │   ├── import/
    │   │   ├── page.tsx       # Import list + file upload (/import)
    │   │   └── [importId]/page.tsx   # Import detail + stage timeline + duplicate review
    │   ├── transactions/page.tsx     # Transaction list with filters (/transactions)
    │   ├── reports/
    │   │   ├── page.tsx       # Report index (/reports)
    │   │   └── [yearMonth]/page.tsx  # Monthly report detail with charts
    │   ├── budgets/
    │   │   ├── page.tsx       # Budget index (/budgets)
    │   │   └── [yearMonth]/page.tsx  # Budget detail per month
    │   ├── query/page.tsx     # Natural-language Q&A (/query)
    │   ├── settings/page.tsx  # LLM runtime config (/settings)
    │   └── components/        # Shared UI primitives
    └── lib/
        └── api.ts             # All fetch calls + TypeScript types for all API responses
```

---

## Backend Directory Purposes

### `backend/app/core/`
Cross-cutting utilities with no business or framework dependencies.

| File | Role |
|------|------|
| `config.py` | `Settings` (pydantic-settings), reads `.env`; exposes `settings` singleton |
| `exceptions.py` | `ParseError`, `UnsupportedFormatError`, `ImportNotFoundError` |
| `event_bus.py` | In-memory `EventBus`, `DomainEvent` base, typed events (currently not subscribed) |
| `logging.py` | `setup_logging(debug)` configures stdlib logging |
| `timezone.py` | `now_beijing()`, `isoformat_beijing()`, `ensure_beijing_naive()` |

### `backend/app/domain/`
Pure Python — no SQLAlchemy, no FastAPI, no HTTP.

| Path | Role |
|------|------|
| `transaction/models.py` | `RawTransaction`, `Transaction` dataclasses; `BillSource`, `TransactionDirection`, `CategorySource` enums; `build_transaction_dedupe_key()` |
| `classification/pipeline.py` | `ClassificationPipeline` (Chain of Responsibility); `ClassificationStage` ABC; four concrete stages |
| `classification/batch_runner.py` | `classify_transactions()` — concurrent batch execution with `BatchProgressUpdate` callbacks |
| `classification/rule_engine.py` | `Rule`, `RuleEngine`, `SYSTEM_RULES` (500+ keyword→category mappings) |
| `classification/category_tree.py` | `CATEGORY_TREE` dict, `L1_CATEGORIES` list, `is_valid_l1()`, `get_l2_options()`, `category_tree_for_prompt()` |
| `beancount/engine.py` | `BeancountEngine.generate_entry()` → `BeancountEntry`; `render_ledger()` for full-month export |
| `beancount/account_resolver.py` | Maps `(source, category_l1, category_l2)` to Beancount account strings |

### `backend/app/application/`
Orchestration services — each maps to a feature domain.

| File | Role |
|------|------|
| `import_service.py` | `submit_import()` — save file, detect format, create DB record, enqueue Celery; `get_import_status()`, `resolve_duplicate_review_group()`, `delete_import()` |
| `report_service.py` | `get_or_generate_report()` — cache-first, calls `InsightAgent`; `list_available_months()`, `get_category_trends()` |
| `budget_service.py` | `get_or_generate_budget_plan()` — statistical budget recommendations from 6-month rolling window |
| `runtime_settings_service.py` | `get_runtime_settings()`, `update_runtime_settings()` — LLM provider/model/key management |
| `query_service.py` | `answer_question()` — regex intent detection + direct SQL aggregation; no LLM |

### `backend/app/infrastructure/`

#### `parsers/`
| File | Role |
|------|------|
| `base.py` | `BillParserAdapter` ABC with `can_parse()`, `can_parse_file()`, `parse()`, `parse_file()`, `source_type` |
| `registry.py` | `register()`, `auto_detect_file()`, `parse_file()` — parser plugin registry |
| `wechat.py` | WeChat Pay CSV and XLSX parser (`source_type = "wechat"`) |
| `alipay.py` | Alipay CSV parser (GBK/GB18030 encoding; multiple header row formats) |
| `cmb.py` | China Merchants Bank PDF parser (PyMuPDF text extraction; RapidOCR fallback) |
| `__init__.py` | `import alipay, cmb, wechat` to trigger self-registration |

#### `ai/`
| File | Role |
|------|------|
| `base.py` | `LLMAdapter` ABC, `LLMMessage`, `LLMUsage` dataclasses |
| `adapter_protocol.py` | Protocol type for structural typing |
| `claude_client.py` | `ClaudeClient` — wraps `anthropic` SDK |
| `deepseek_client.py` | `DeepSeekClient` — wraps `openai` SDK with DeepSeek base URL |
| `factory.py` | `create_llm_client(provider, api_key, base_url, model)` |
| `agents/base.py` | `BaseAgent` with `run()` contract |
| `agents/classification_agent.py` | `ClassificationAgent` — batch LLM classification with structured JSON output |
| `agents/insight_agent.py` | `InsightAgent` — generates Chinese-language monthly financial narrative |
| `agents/registry.py` | `AgentRegistry` — pluggable agent lookup (not wired in production) |

#### `persistence/`
| File | Role |
|------|------|
| `database.py` | SQLAlchemy engine + `SessionLocal` factory + `get_db()` FastAPI dependency |
| `models/orm_models.py` | All 12 ORM models (UserORM, BillImportORM, ImportStageORM, ImportSummaryORM, TransactionORM, DuplicateReviewGroupORM, BeancountEntryORM, CategoryRuleORM, RuleSuggestionORM, MonthlyReportORM, BudgetPlanORM, RuntimeSettingORM) |
| `repositories/transaction_repo.py` | Single repository with all DB read/write operations across all feature domains |

#### `queue/`
| File | Role |
|------|------|
| `celery_app.py` | `Celery` app configured with Redis broker/backend; routes `import_tasks.process_bill_import` to `"imports"` queue |
| `import_tasks.py` | `process_bill_import` Celery task (5-stage pipeline); `resume_import_after_duplicate_review()`; `_continue_import_after_duplicate_review()`; `_build_pipeline()` |

### `backend/app/api/v1/`
One file per feature domain, all mounted at `/api/v1` prefix.

| File | Prefix | Key Endpoints |
|------|--------|---------------|
| `bills.py` | `/bills` | import upload, status poll, detail, duplicate-review resolve, delete, list |
| `transactions.py` | `/transactions` | list (paginated, filtered), category update, summary |
| `reports.py` | `/reports` | monthly report, available months, merchant ranking, category trends, Beancount export |
| `categories.py` | `/categories` | category tree, CRUD rules, rule suggestions CRUD + generate + approve/reject |
| `budgets.py` | `/budgets` | get/generate budget plan |
| `settings.py` | `/settings` | get/update runtime LLM config |
| `query.py` | `/query` | natural-language finance Q&A |

---

## Frontend Directory Purposes

### `app/` (Next.js App Router)

All pages are React Server Component shells with `"use client"` directives for interactive sections. SWR handles all server-state fetching and polling.

| Path | Route | Purpose |
|------|-------|---------|
| `layout.tsx` | All routes | Root layout: `<Sidebar>` + `<main>` wrapper |
| `page.tsx` | `/` | Dashboard: stats, recent imports, budget snapshot, quick actions |
| `import/page.tsx` | `/import` | File upload (drag-and-drop + file picker), import list with live status badges |
| `import/[importId]/page.tsx` | `/import/:id` | Import detail: stage timeline, progress bars, duplicate review UI, AI classification stats |
| `transactions/page.tsx` | `/transactions` | Paginated transaction table with filters (month, category, direction); inline category edit |
| `reports/page.tsx` | `/reports` | List of months with report data |
| `reports/[yearMonth]/page.tsx` | `/reports/:ym` | Monthly financial report: pie chart, merchant ranking, weekly bar chart, AI insight |
| `budgets/page.tsx` | `/budgets` | List of budget periods |
| `budgets/[yearMonth]/page.tsx` | `/budgets/:ym` | Per-month budget breakdown with progress bars and status indicators |
| `query/page.tsx` | `/query` | Chat-style natural-language query form + answer display |
| `settings/page.tsx` | `/settings` | LLM provider/model/API key form + throughput tuning |

### `app/components/`
Shared presentational primitives — no data fetching.

| File | Exports |
|------|---------|
| `Sidebar.tsx` | `Sidebar` — responsive nav with mobile drawer; nav links defined in `NAV` array |
| `Badge.tsx` | `SourceBadge`, `StatusBadge` — colored tags for import source and lifecycle status |
| `Card.tsx` | `Card` (variants: surface/elevated/bordered), `cx()` utility, `cardClassName` |
| `StatCard.tsx` | `StatCard` — labeled metric card with tone (rose/emerald/gold) |
| `ProgressBar.tsx` | `ProgressBar` — labeled progress bar with tone variants |
| `PageHeader.tsx` | `PageHeader` — eyebrow + title + description + optional action slot |
| `EmptyState.tsx` | `EmptyState` — empty placeholder with optional action |

### `lib/`
| File | Role |
|------|------|
| `api.ts` | `request<T>()` generic fetch wrapper; all typed API call functions; all TypeScript interface definitions for API request/response shapes |

---

## Alembic Migrations

Location: `backend/alembic/versions/`

| Migration | Summary |
|-----------|---------|
| `001_initial_schema.py` | users, bill_imports, transactions, category_rules, beancount_entries, monthly_reports |
| `002_add_transaction_external_id.py` | `external_id` + unique constraint on transactions |
| `003_add_budget_plans.py` | budget_plans table |
| `004_add_rule_suggestions.py` | rule_suggestions table |
| `005_add_runtime_settings_and_import_progress.py` | runtime_settings, LLM token columns on bill_imports |
| `006_add_transaction_cross_source_dedupe_key.py` | `dedupe_key` + unique constraint on transactions |
| `007_add_import_stages_and_summaries.py` | import_stages, import_summaries tables |
| `008_add_duplicate_review_foundations.py` | duplicate_review_groups, `duplicate_review_status`/`duplicate_review_group_id` on transactions |

Run with: `uv run alembic upgrade head` (automated in Docker via `migrate` service).

---

## Naming Conventions

### Backend
- **Files:** `snake_case.py`; suffix `_service.py` for application layer, `_repo.py` for repositories, `_agent.py` for AI agents, `_tasks.py` for Celery tasks
- **Classes:** `PascalCase`; ORM models suffixed `ORM` (e.g., `TransactionORM`)
- **Domain models:** plain dataclasses without suffix (`RawTransaction`, `Transaction`)
- **Enums:** `PascalCase` extending `str, Enum`

### Frontend
- **Files:** `PascalCase.tsx` for components; `camelCase.ts` for utilities
- **Pages:** `page.tsx` (Next.js convention)
- **API functions:** `verbNoun` camelCase (e.g., `importBill`, `listTransactions`, `getMonthlyReport`)
- **Types/Interfaces:** `PascalCase` with full semantic names (e.g., `ImportDetail`, `DuplicateReviewGroup`)

---

## Where to Add New Code

### New bill source (parser)
1. Create `backend/app/infrastructure/parsers/{source}.py` implementing `BillParserAdapter`.
2. Add `from app.infrastructure.parsers import {source}` in `backend/app/infrastructure/parsers/__init__.py`.
3. Parser auto-registers via `registry.register()` call at module import time.
4. Add `BillSource.{SOURCE}` to `backend/app/domain/transaction/models.py`.
5. Add Beancount asset account mapping in `backend/app/domain/beancount/account_resolver.py`.

### New API endpoint
1. Add route to the appropriate `backend/app/api/v1/{feature}.py` router.
2. Add business logic to `backend/app/application/{feature}_service.py`.
3. Add DB operations to `backend/app/infrastructure/persistence/repositories/transaction_repo.py`.
4. Add TypeScript client function + types to `frontend/lib/api.ts`.
5. Create or update the relevant page in `frontend/app/{feature}/page.tsx`.

### New LLM agent
1. Create `backend/app/infrastructure/ai/agents/{name}_agent.py` extending `BaseAgent`.
2. Register with `AgentRegistry` if needed.
3. Instantiate via `create_llm_client()` factory.

### New database column
1. Create a new migration: `uv run alembic revision -m "description"`.
2. Add column to the relevant ORM class in `orm_models.py`.
3. Add read/write operations in `transaction_repo.py`.

### New frontend page
1. Create `frontend/app/{route}/page.tsx` (Next.js App Router file-based routing).
2. Add nav link to `NAV` array in `frontend/app/components/Sidebar.tsx`.
3. Use `useSWR` + functions from `lib/api.ts` for data fetching.

### New category
1. Add to `CATEGORY_TREE` dict in `backend/app/domain/classification/category_tree.py`.
2. Optionally add keyword rules to `SYSTEM_RULES` in `backend/app/domain/classification/rule_engine.py`.
3. Add Beancount account mapping in `backend/app/domain/beancount/account_resolver.py`.

---

## Special Directories

### `backend/uploads/`
- Purpose: Temporary storage for uploaded bill files during async processing.
- Generated: At runtime, created by `import_service.submit_import()`.
- Committed: No. Listed in `.gitignore`.
- Docker: Shared between `backend` and `worker` containers via named volume `uploads`.

### `backend/alembic/versions/`
- Purpose: Sequential database migration scripts.
- Generated: Partially via `alembic revision`; hand-edited for column details.
- Committed: Yes.

### `frontend/.next/`
- Purpose: Next.js build cache and output.
- Generated: By `pnpm build`.
- Committed: No.

### `.planning/codebase/`
- Purpose: GSD architecture and convention reference docs for AI-assisted development.
- Generated: By mapping agents.
- Committed: Yes.

---

## Entry Points

| Entry Point | Location | Invocation |
|-------------|----------|------------|
| FastAPI application | `backend/app/main.py` | `uvicorn app.main:app` (via `entrypoint.sh`) |
| Celery worker | `backend/app/infrastructure/queue/celery_app.py` | `celery -A app.infrastructure.queue.celery_app worker -Q imports` |
| Alembic migrations | `backend/alembic/env.py` | `alembic upgrade head` |
| Next.js frontend | `frontend/app/layout.tsx` + `frontend/app/page.tsx` | `next start` (standalone mode) |

---

## Gaps & Unknowns

- `backend/main.py` (root) is a stub that prints "Hello from backend!" — it is not the production entry point; the real entry is `backend/app/main.py`.
- `AgentRegistry` exists (`infrastructure/ai/agents/registry.py`) but is not used in any production code path.
- `EventBus` subscriptions are never wired; the bus is instantiated but has no handlers.
- There are no frontend tests; no Playwright E2E setup.
- `backend/tests/` contains only 4 test files (parsers, category suggestions, import detail, deduplication) — test coverage for application and domain layers is minimal.
