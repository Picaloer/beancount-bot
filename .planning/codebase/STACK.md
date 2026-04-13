# Technology Stack

_Last updated: 2026-04-13_

## Summary

Beancount Bot is a full-stack monorepo with a Python FastAPI backend and a Next.js frontend, deployed as five Docker services. The backend handles async bill import, LLM-based classification, and double-entry bookkeeping generation; the frontend provides a React data-visualization UI. All services communicate over HTTP/JSON.

---

## Languages

**Primary:**
- Python 3.13 — backend API, workers, domain logic, parsers
  - Version pinned in `backend/.python-version`
- TypeScript 5.x — frontend (all `.ts` / `.tsx` files)

**Secondary:**
- SQL — database schema and migrations (Alembic + PostgreSQL dialect)
- Shell — `backend/entrypoint.sh` (startup readiness probe)

---

## Runtime

**Backend Environment:**
- CPython 3.13 (`python:3.13-slim` Docker base image — see `backend/Dockerfile`)
- ASGI server: **Uvicorn** `>=0.42.0` (with `standard` extras for HTTP/2 support)

**Frontend Environment:**
- Node.js 22-alpine (Docker base image — see `frontend/Dockerfile`)
- Output mode: `standalone` (`frontend/next.config.ts`)

---

## Package Managers

**Backend:** `uv` (Astral's pip replacement)
- Lockfile: `backend/uv.lock` (committed)
- Run commands: `uv run <command>` (not `python -m` or direct activation)
- Install: `uv sync --frozen --no-dev --no-install-project`

**Frontend:** `pnpm` (via Node corepack, latest version)
- Lockfile: `frontend/pnpm-lock.yaml` (committed)
- Workspace config: `frontend/pnpm-workspace.yaml`

---

## Frameworks

**Web API:**
- **FastAPI** `>=0.135.2` — REST API framework
  - Entry point: `backend/app/main.py`
  - Routers: `backend/app/api/v1/` (bills, transactions, reports, categories, query, budgets, settings)
  - CORS middleware: allows `http://localhost:3000` and `http://127.0.0.1:3000`
  - Served via Uvicorn on port 8000

**Frontend:**
- **Next.js** `16.2.1` (App Router) — React SSR/SSG framework
  - Note: This is a newer version with breaking API changes; see `frontend/AGENTS.md`
  - Served as standalone Node.js bundle on port 3000
- **React** `19.2.4` / **react-dom** `19.2.4`

**Task Queue:**
- **Celery** `>=5.6.3` with Redis broker (`celery[redis]`)
  - App definition: `backend/app/infrastructure/queue/celery_app.py`
  - Queue: `imports` (worker listens exclusively to this queue)
  - Concurrency: 2 workers (configured in `docker-compose.yml`)
  - Task: `import_tasks.process_bill_import`

---

## Key Backend Dependencies

**Data / Persistence:**
- **SQLAlchemy** `>=2.0.48` — ORM with declarative mapped columns
  - Pool: `pool_size=10`, `max_overflow=20` for PostgreSQL; `StaticPool` for SQLite (test)
  - Models: `backend/app/infrastructure/persistence/models/orm_models.py`
- **psycopg2-binary** `>=2.9.11` — PostgreSQL sync driver
- **Alembic** `>=1.18.4` — database migrations (`backend/alembic/`)

**Configuration / Validation:**
- **Pydantic** `>=2.12.5` — request/response schemas and domain models
- **pydantic-settings** `>=2.13.1` — typed env/config loading (`backend/app/core/config.py`)
- **python-dotenv** `>=1.2.2` — `.env` file loading (used by pydantic-settings)

**LLM / AI:**
- **anthropic** `>=0.86.0` — Anthropic Python SDK for Claude API
- **openai** `>=1.0.0` — OpenAI-compatible client (used for DeepSeek via base_url override)

**File Parsing:**
- **openpyxl** `>=3.1.5` — WeChat `.xlsx` bill parsing
- **chardet** `>=7.4.0.post1` — encoding detection for Alipay CSV files (GBK/GB18030/UTF-8)
- **pypdf** `>=6.9.2` — PDF utilities (complementary to PyMuPDF)
- **pymupdf** `>=1.27.2.2` (`fitz`) — PDF text extraction for CMB statements (primary)
- **rapidocr-onnxruntime** `>=1.4.4` — OCR fallback for scanned CMB PDFs
- **pypdfium2** `>=5.6.0` — auxiliary PDF rendering

**Networking:**
- **python-multipart** `>=0.0.22` — multipart form data (file uploads in FastAPI)
- **redis** `>=6.4.0` — Redis Python client (Celery backend)

**Dev / Test:**
- **pytest** `>=9.0.2`
- **pytest-asyncio** `>=1.3.0`
- **httpx** `>=0.28.1` — async HTTP client for integration tests

---

## Key Frontend Dependencies

**Data Fetching:**
- **SWR** `^2.4.1` — React data fetching with stale-while-revalidate; used on nearly every page (see `frontend/app/*/page.tsx`)
- `fetch` native browser API — raw API calls in `frontend/lib/api.ts`

**Data Visualization:**
- **Recharts** `^3.8.1` — charts for monthly reports (`frontend/app/reports/[yearMonth]/page.tsx`)

**Styling:**
- **Tailwind CSS** `^4` — utility-first CSS
- **@tailwindcss/postcss** `^4` — PostCSS plugin (`frontend/postcss.config.mjs`)

**Linting:**
- **ESLint** `^9` with `eslint-config-next` `16.2.1` (core-web-vitals + TypeScript rules)
  - Config: `frontend/eslint.config.mjs`

**TypeScript:**
- Strict mode enabled (`"strict": true` in `frontend/tsconfig.json`)
- Path alias: `@/*` → `./` (project root)
- Module resolution: `bundler`

---

## Infrastructure

**Databases:**
- **PostgreSQL 16-alpine** — primary data store (`postgres:16-alpine` image, `docker-compose.yml`)
  - DB name: `beancount_bot`
  - Default credentials: `postgres/postgres` (for local dev only)
  - Data volume: `postgres_data`

**Cache / Message Broker:**
- **Redis 7-alpine** — Celery broker + result backend (`redis:7-alpine` image, `docker-compose.yml`)
  - Data volume: `redis_data`
  - Default URL: `redis://redis:6379/0`

**File Storage:**
- Local filesystem volume `uploads` — shared between `backend` and `worker` containers
  - Path inside containers: `/app/uploads`
  - Env var: `UPLOAD_DIR`

---

## Deployment

**Container Orchestration:**
- **Docker Compose** — `docker-compose.yml` defines 5 services:
  1. `postgres` — PostgreSQL
  2. `redis` — Redis
  3. `migrate` — one-shot Alembic migration runner (`alembic upgrade head`)
  4. `backend` — FastAPI on port 8000
  5. `worker` — Celery worker (queue: `imports`, concurrency: 2)
  6. `frontend` — Next.js standalone on port 3000

**Build:**
- Backend: `python:3.13-slim` + `uv` binary from `ghcr.io/astral-sh/uv:latest`
- Frontend: multi-stage (deps → builder → runner); `NEXT_PUBLIC_API_URL` embedded at build time

**Startup Orchestration:**
- `backend/entrypoint.sh` — polls PostgreSQL with SQLAlchemy `SELECT 1` before starting Uvicorn
- Docker Compose healthchecks on both `postgres` and `redis` guard `backend`, `worker`, and `migrate`

**Operations (Makefile):**
- `make setup` — copy `.env.example` → `.env`
- `make up` — build images, run migrations, start all services
- `make migrate` — run Alembic migrations only
- `make clean` — destroy all containers + volumes (destructive)
- Located at: `Makefile` (project root)

---

## Configuration

**Environment Variables (root `.env` file, required):**
- `ANTHROPIC_API_KEY` — required when `LLM_PROVIDER=claude`
- `DEEPSEEK_API_KEY` — required when `LLM_PROVIDER=deepseek`
- `LLM_PROVIDER` — `claude` (default) or `deepseek`
- `LLM_MODEL` — defaults to `claude-haiku-4-5-20251001`
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `NEXT_PUBLIC_API_URL` — injected at Next.js build time (defaults to `http://localhost:8000/api/v1`)

**Frontend local config:**
- `frontend/.env.local` / `frontend/.env.local.example` — local overrides for `NEXT_PUBLIC_API_URL`

**Backend settings source:**
- `backend/app/core/config.py` — `pydantic_settings.BaseSettings`, reads `.env` + environment
- Runtime-overridable LLM settings persisted in `runtime_settings` DB table (see `RuntimeSettingORM`)

---

## Development Tooling

- No CI/CD pipeline detected (no `.github/workflows/`)
- No linter config for Python (no `.ruff.toml`, `.flake8`, `pyproject.toml` `[tool.ruff]` section)
- TypeScript type checking: `tsc --noEmit` (via `frontend/tsconfig.json`, strict mode)
- Backend tests run with `uv run pytest` from `backend/` directory
- Test files: `backend/tests/` (unit + integration subdirs)

---

## Gaps & Unknowns

- No CI/CD pipeline configured — no `.github/workflows/` directory exists
- No Python linter/formatter config found (`ruff`, `black`, `mypy` not in `pyproject.toml`)
- No frontend test framework configured (`jest`, `vitest`, or `playwright` not in `package.json`)
- `pnpm-workspace.yaml` is present but appears to manage a single-package workspace
- `rapidocr-onnxruntime` requires system library `libxcb1`; not installed in Dockerfile — OCR may silently fail in Docker unless added
