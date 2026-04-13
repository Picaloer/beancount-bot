## 开发守则

1. 开发新功能时需要从master中切出新分支, 在该分支上开发完毕后, 进行充分回归测试, 随后merge到master分支上
分支命名遵守如下
- feat: 新增功能
- fix: 修复 bug
- merge: 代码合并
- docs: 仅仅修改了文档，比如 README, CHANGELOG等等
- test: 增加/修改测试用例，包括单元测试、集成测试等
- style: 修改了空行、缩进格式、引用包排序等等（不改变代码逻辑）
- perf: 优化相关内容，比如提升性能、体验、算法等
- refactor: 代码重构，「没有新功能或者bug修复」
- chore: 改变构建流程、或者增加依赖库、工具等
- revert: 回滚到上一个版本

2. 当 beancount-bot 支持新类型的文件导入时， 需要你同步后端前端进行适配对应文件格式的上传。

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Beancount Bot**

Beancount Bot is an AI-powered personal finance management system. It ingests bill exports from WeChat Pay, Alipay, bank cards (CMB, ICBC, CEB, etc.) and other payment channels, automatically classifies transactions using a rule+LLM pipeline, and generates Beancount double-entry journal entries. It provides monthly spend summaries and AI insights — without requiring accounting expertise from the user.

**Core Value:** A user can import all their bills from multiple channels and get an accurate, deduplicated picture of where their money actually went this month.

### Constraints

- **Tech stack**: Python 3.13 / FastAPI / SQLAlchemy / PostgreSQL / Celery + Redis (backend); Next.js 16 App Router / TypeScript / Tailwind CSS / SWR (frontend) — no new runtimes
- **Package managers**: `uv` (backend), `pnpm` (frontend)
- **LLM**: Claude (claude-haiku-4-5-20251001 default) or DeepSeek via OpenAI-compatible client
- **Deployment**: Docker Compose, single-node
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Summary
## Languages
- Python 3.13 — backend API, workers, domain logic, parsers
- TypeScript 5.x — frontend (all `.ts` / `.tsx` files)
- SQL — database schema and migrations (Alembic + PostgreSQL dialect)
- Shell — `backend/entrypoint.sh` (startup readiness probe)
## Runtime
- CPython 3.13 (`python:3.13-slim` Docker base image — see `backend/Dockerfile`)
- ASGI server: **Uvicorn** `>=0.42.0` (with `standard` extras for HTTP/2 support)
- Node.js 22-alpine (Docker base image — see `frontend/Dockerfile`)
- Output mode: `standalone` (`frontend/next.config.ts`)
## Package Managers
- Lockfile: `backend/uv.lock` (committed)
- Run commands: `uv run <command>` (not `python -m` or direct activation)
- Install: `uv sync --frozen --no-dev --no-install-project`
- Lockfile: `frontend/pnpm-lock.yaml` (committed)
- Workspace config: `frontend/pnpm-workspace.yaml`
## Frameworks
- **FastAPI** `>=0.135.2` — REST API framework
- **Next.js** `16.2.1` (App Router) — React SSR/SSG framework
- **React** `19.2.4` / **react-dom** `19.2.4`
- **Celery** `>=5.6.3` with Redis broker (`celery[redis]`)
## Key Backend Dependencies
- **SQLAlchemy** `>=2.0.48` — ORM with declarative mapped columns
- **psycopg2-binary** `>=2.9.11` — PostgreSQL sync driver
- **Alembic** `>=1.18.4` — database migrations (`backend/alembic/`)
- **Pydantic** `>=2.12.5` — request/response schemas and domain models
- **pydantic-settings** `>=2.13.1` — typed env/config loading (`backend/app/core/config.py`)
- **python-dotenv** `>=1.2.2` — `.env` file loading (used by pydantic-settings)
- **anthropic** `>=0.86.0` — Anthropic Python SDK for Claude API
- **openai** `>=1.0.0` — OpenAI-compatible client (used for DeepSeek via base_url override)
- **openpyxl** `>=3.1.5` — WeChat `.xlsx` bill parsing
- **chardet** `>=7.4.0.post1` — encoding detection for Alipay CSV files (GBK/GB18030/UTF-8)
- **pypdf** `>=6.9.2` — PDF utilities (complementary to PyMuPDF)
- **pymupdf** `>=1.27.2.2` (`fitz`) — PDF text extraction for CMB statements (primary)
- **rapidocr-onnxruntime** `>=1.4.4` — OCR fallback for scanned CMB PDFs
- **pypdfium2** `>=5.6.0` — auxiliary PDF rendering
- **python-multipart** `>=0.0.22` — multipart form data (file uploads in FastAPI)
- **redis** `>=6.4.0` — Redis Python client (Celery backend)
- **pytest** `>=9.0.2`
- **pytest-asyncio** `>=1.3.0`
- **httpx** `>=0.28.1` — async HTTP client for integration tests
## Key Frontend Dependencies
- **SWR** `^2.4.1` — React data fetching with stale-while-revalidate; used on nearly every page (see `frontend/app/*/page.tsx`)
- `fetch` native browser API — raw API calls in `frontend/lib/api.ts`
- **Recharts** `^3.8.1` — charts for monthly reports (`frontend/app/reports/[yearMonth]/page.tsx`)
- **Tailwind CSS** `^4` — utility-first CSS
- **@tailwindcss/postcss** `^4` — PostCSS plugin (`frontend/postcss.config.mjs`)
- **ESLint** `^9` with `eslint-config-next` `16.2.1` (core-web-vitals + TypeScript rules)
- Strict mode enabled (`"strict": true` in `frontend/tsconfig.json`)
- Path alias: `@/*` → `./` (project root)
- Module resolution: `bundler`
## Infrastructure
- **PostgreSQL 16-alpine** — primary data store (`postgres:16-alpine` image, `docker-compose.yml`)
- **Redis 7-alpine** — Celery broker + result backend (`redis:7-alpine` image, `docker-compose.yml`)
- Local filesystem volume `uploads` — shared between `backend` and `worker` containers
## Deployment
- **Docker Compose** — `docker-compose.yml` defines 5 services:
- Backend: `python:3.13-slim` + `uv` binary from `ghcr.io/astral-sh/uv:latest`
- Frontend: multi-stage (deps → builder → runner); `NEXT_PUBLIC_API_URL` embedded at build time
- `backend/entrypoint.sh` — polls PostgreSQL with SQLAlchemy `SELECT 1` before starting Uvicorn
- Docker Compose healthchecks on both `postgres` and `redis` guard `backend`, `worker`, and `migrate`
- `make setup` — copy `.env.example` → `.env`
- `make up` — build images, run migrations, start all services
- `make migrate` — run Alembic migrations only
- `make clean` — destroy all containers + volumes (destructive)
- Located at: `Makefile` (project root)
## Configuration
- `ANTHROPIC_API_KEY` — required when `LLM_PROVIDER=claude`
- `DEEPSEEK_API_KEY` — required when `LLM_PROVIDER=deepseek`
- `LLM_PROVIDER` — `claude` (default) or `deepseek`
- `LLM_MODEL` — defaults to `claude-haiku-4-5-20251001`
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `NEXT_PUBLIC_API_URL` — injected at Next.js build time (defaults to `http://localhost:8000/api/v1`)
- `frontend/.env.local` / `frontend/.env.local.example` — local overrides for `NEXT_PUBLIC_API_URL`
- `backend/app/core/config.py` — `pydantic_settings.BaseSettings`, reads `.env` + environment
- Runtime-overridable LLM settings persisted in `runtime_settings` DB table (see `RuntimeSettingORM`)
## Development Tooling
- No CI/CD pipeline detected (no `.github/workflows/`)
- No linter config for Python (no `.ruff.toml`, `.flake8`, `pyproject.toml` `[tool.ruff]` section)
- TypeScript type checking: `tsc --noEmit` (via `frontend/tsconfig.json`, strict mode)
- Backend tests run with `uv run pytest` from `backend/` directory
- Test files: `backend/tests/` (unit + integration subdirs)
## Gaps & Unknowns
- No CI/CD pipeline configured — no `.github/workflows/` directory exists
- No Python linter/formatter config found (`ruff`, `black`, `mypy` not in `pyproject.toml`)
- No frontend test framework configured (`jest`, `vitest`, or `playwright` not in `package.json`)
- `pnpm-workspace.yaml` is present but appears to manage a single-package workspace
- `rapidocr-onnxruntime` requires system library `libxcb1`; not installed in Dockerfile — OCR may silently fail in Docker unless added
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Summary
## Backend (Python)
### Naming Patterns
- Module names: `snake_case` — `import_service.py`, `transaction_repo.py`, `claude_client.py`
- ORM model files: `orm_models.py` (all models in one file per layer)
- Test files: `test_<feature>.py` — `test_category_suggestions.py`, `test_import_detail.py`
- PascalCase: `BillParserAdapter`, `ClassificationPipeline`, `TransactionORM`, `BeancountEngine`
- ORM classes suffixed with `ORM`: `TransactionORM`, `BillImportORM`, `CategoryRuleORM`
- Domain dataclasses unsuffixed: `RawTransaction`, `Transaction`, `ClassificationResult`
- ABC base classes: `BillParserAdapter(ABC)`, `ClassificationStage(ABC)`, `AIAgent(ABC)`
- `snake_case`: `submit_import`, `bulk_create_transactions`, `auto_detect_file`, `setup_logging`
- Private helpers prefixed with `_`: `_serialize`, `_read_text_candidates`, `_normalize_dedupe_text`
- Module-level logger: `logger = logging.getLogger(__name__)` at top of each module that needs logging
- `snake_case` throughout
- Constants: `UPPERCASE` — `SYSTEM_RULES`, `USER_ID` in tests
- Enum values: lowercase strings matching domain vocabulary — `"expense"`, `"wechat"`, `"user_rule"`
- All enums inherit from both `str` and `Enum`: `class TransactionDirection(str, Enum)`
- Values are lowercase strings: `EXPENSE = "expense"`, `WECHAT = "wechat"`
### Type Annotations
### Import Organization
### Error Handling
### Logging
- Setup: `backend/app/core/logging.py` — single `setup_logging(debug: bool)` call at startup
- Format: `"%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"` to `sys.stdout`
- Module loggers: `logger = logging.getLogger(__name__)` at module level
- Log call style: `%`-style formatting (never f-strings in log calls):
- Library silencing: SQLAlchemy engine at WARNING; httpx at WARNING; celery at INFO
### Comments and Docstrings
- Module docstrings: short one-liner or brief explanatory block at the top of complex modules:
- Inline comments: used for context that the code alone doesn't convey — `# Quiet noisy libraries`, `# noqa: F401 – register ORM models`
- Function-level docstrings: present on public API endpoints and key service methods:
- No JSDoc/Sphinx-style docstrings in the codebase.
### Data Modeling
### Architecture Conventions
- Layers are enforced by import direction: `api` → `application` → `domain` (no framework imports). Infrastructure adapts domain abstractions.
- Registry pattern for parsers: `register(parser)` → `auto_detect_file(path)`.
- ABC base classes define contracts: `BillParserAdapter(ABC)`, `ClassificationStage(ABC)`, `AIAgent(ABC)`.
- Chain of Responsibility for classification: `UserDefinedRuleStage → SystemRuleStage → LLMStage → FallbackStage`.
- Dependency injection at API level via FastAPI `Depends(get_db)`.
- Single-user MVP: `settings.default_user_id = "00000000-0000-0000-0000-000000000001"` used everywhere in lieu of auth.
## Frontend (TypeScript / React)
### Naming Patterns
- Next.js pages: `page.tsx` in feature directories — `app/import/page.tsx`, `app/reports/[yearMonth]/page.tsx`
- Shared components: `PascalCase.tsx` — `Badge.tsx`, `Card.tsx`, `EmptyState.tsx`, `PageHeader.tsx`
- API layer: `lib/api.ts` (single file)
- Dynamic route segments: `[paramName]` directory convention — `app/import/[importId]/page.tsx`
- PascalCase, named exports for reusable components: `export function SourceBadge(...)`, `export default function Card(...)`
- Sub-components (local to a page file) are defined as plain functions in the same file: `function MetricChip(...)`, `function ImportProgress(...)`, `function MessageCard(...)`
- All API response types declared as `export interface` in `lib/api.ts`
- Props typed inline (no separate `*Props` type files): `{ children: ReactNode; className?: string; variant?: CardVariant }`
- String literal unions preferred over enums: `"surface" | "elevated" | "bordered"`, `"expense" | "income" | "transfer"`
- `type` aliases for unions: `export type CardVariant = "surface" | "elevated" | "bordered"`, `export type ImportLifecycleStatus = ...`
- `camelCase` for all functions and event handlers: `handleFile`, `handleDelete`, `onDrop`, `formatImportTime`
- Boolean helpers: named `canXxx` / `isXxx`: `canDeleteImport`, `isTerminalStatus`
- Utility functions at file bottom: `formatImportTime`, `formatNumber`, `sourceLabel`, `calculateProgress`
- `camelCase`: `fileRef`, `statusData`, `primaryButtonClassName`
- Constants (module-level strings): `camelCase` with `const`: `primaryButtonClassName`, `secondaryButtonClassName`
### TypeScript Usage
- `unknown` used for caught errors, narrowed with `instanceof Error`:
- No `any` in production code
- Props types are inline object types on function parameters (no separate `interface FooProps`)
- `React.FC` not used; plain function components with explicit props typing
- `void` used to explicitly discard floating promises: `void handleFile(file)`, `void mutateImports()`
### Import Organization
### API Layer Pattern
### Error Handling (Frontend)
- Component-level error state: `const [error, setError] = useState<string | null>(null)`
- Always clear error before async operation: `setError(null)`
- Narrow caught `unknown`: `e instanceof Error ? e.message : "fallback message"`
- Never use `console.log` in production code; no `console.*` calls found in application source
### State and Data Fetching
- SWR for server state: `useSWR(key, fetcher, options)` — polling interval controlled by data:
- Local UI state: `useState` for loading flags, selection state, error messages
- `useRef` for DOM references (file input)
### Styling
- Tailwind CSS 4 utility classes throughout
- CSS custom properties for design tokens: `var(--gold-400)`, `var(--text-primary)`, `var(--bg-surface)`, `var(--border-default)`
- `cx(...)` utility from `Card.tsx` for conditional class joining (no external library like `clsx`):
- Inline Tailwind arbitrary values widely used: `bg-[rgba(212,168,67,0.08)]`, `rounded-[28px]`
### Component Conventions
- `"use client"` directive on all interactive page components
- Default export for pages, named exports for reusable shared components
- SVG icons defined as inline function components at the bottom of the file using them: `function UploadGlyph({ className })`
- Component props: `className?: string` accepted by all reusable components for composability
- Variant maps for badges/cards use `Record<string, string>` rather than switch statements
## Gaps & Unknowns
- No `ruff.toml`, `pyproject.toml` `[tool.ruff]` section, `.flake8`, or `mypy.ini` found — linting/formatting rules are not enforced in the repo configuration (relies on developer's global tools).
- No Prettier config (`.prettierrc`, `prettier.config.*`) in `frontend/` — formatting is not auto-enforced in repo.
- No `[tool.pytest.ini_options]` section in `pyproject.toml` — pytest options (asyncio mode, test paths) must be passed on the command line or are absent.
- Some functions in the API layer have inline imports (`from sqlalchemy import select`) rather than top-level imports; this is inconsistent and may indicate refactoring backlog.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Summary
## High-Level Component Diagram
```
```
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
### Infrastructure Layer
- Purpose: Adapters for all external systems.
- Location: `backend/app/infrastructure/`
- Sub-packages:
### Core
- Purpose: Cross-cutting concerns.
- Location: `backend/app/core/`
- Contains: `config.py` (pydantic-settings `Settings` singleton), `exceptions.py`, `event_bus.py` (in-memory EventBus), `logging.py`, `timezone.py`.
## Import Pipeline (Primary Data Flow)
```
```
## Classification Pipeline (Chain of Responsibility)
```
```
## Deduplication Strategy
- `external_id` — platform-native order number (`交易单号` / `交易订单号`); unique constraint `(user_id, external_id)`.
- `dedupe_key` — SHA-256 hash of `direction|amount|currency|merchant|description|timestamp`; unique constraint `(user_id, dedupe_key)`.
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
## Database Schema (ORM Models)
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
## State Management
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
## Error Handling
- Parse errors → `ParseError` / `UnsupportedFormatError` in `core/exceptions.py` → HTTP 422.
- Import not found → `ImportNotFoundError` → HTTP 404.
- Celery task failures → logged, `bill_imports.status = "failed"`, all stages set to `"failed"`, task retried up to 3 times with 30 s delay.
- LLM errors → caught in `_build_pipeline()`; if LLM unavailable, pipeline falls through to FallbackStage.
- Beancount entry generation failures → logged as warning, entry skipped; import continues.
- `EventBus` handler errors → logged, not re-raised.
## LLM Integration
- Default: `claude-haiku-4-5-20251001` via `anthropic` SDK (`ClaudeClient`).
- Alternate: DeepSeek via OpenAI-compatible endpoint (`DeepSeekClient` using `openai` SDK).
- Runtime switching: `PUT /api/v1/settings/runtime` writes to `runtime_settings` table; next import picks up new config.
- Classification batches: up to `llm_batch_size` (default 20) transactions per API call; up to `llm_max_concurrency` (default 4) concurrent calls.
- Monthly insight: `InsightAgent` runs synchronously inside `report_service.get_or_generate_report()`.
## Deployment
```
```
## Gaps & Unknowns
- `core/event_bus.py` defines `TransactionImported`, `TransactionClassified`, `MonthlyReportRequested` events but no handlers are subscribed; the bus is unused in the current implementation.
- `AgentRegistry` in `infrastructure/ai/agents/registry.py` exists but is not wired into production code.
- The `query_service.py` uses pattern-matching intent detection (no LLM) — it cannot handle free-form questions beyond a fixed set of intents.
- `budget_service._build_budget_recommendations()` is purely statistical (mean + peak buffer); it is labeled "ai" in the source field but does not call an LLM.
- No authentication or per-user isolation beyond the hardcoded `DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"`.
- No test coverage for the Celery task flow end-to-end; tests in `backend/tests/` cover parser and deduplication only.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
