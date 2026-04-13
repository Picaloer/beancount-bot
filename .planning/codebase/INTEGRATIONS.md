# External Integrations

_Last updated: 2026-04-13_

## Summary

Beancount Bot integrates with two LLM providers (Anthropic Claude and DeepSeek) for transaction classification and financial insight generation. All other integrations are self-hosted infrastructure (PostgreSQL, Redis). There are no third-party payment, analytics, monitoring, or auth SaaS providers in use.

---

## LLM / AI Services

### Anthropic Claude API (primary LLM)
- **Purpose:** Transaction classification (`ClassificationAgent`) and monthly financial insight generation (`InsightAgent`)
- **SDK:** `anthropic` Python package `>=0.86.0`
- **Client:** `backend/app/infrastructure/ai/claude_client.py` — wraps `anthropic.Anthropic`
- **Endpoint:** Anthropic default (`https://api.anthropic.com`)
- **Default model:** `claude-haiku-4-5-20251001` (configured in `backend/app/core/config.py` and `docker-compose.yml`)
- **Auth env var:** `ANTHROPIC_API_KEY`
- **Max tokens per call:** 4096
- **Error type caught:** `anthropic.APIError` → re-raised as `LLMError`

### DeepSeek API (alternative LLM)
- **Purpose:** Drop-in alternative LLM provider for classification and insights
- **SDK:** `openai` Python package `>=1.0.0` (OpenAI-compatible client with base URL override)
- **Client:** `backend/app/infrastructure/ai/deepseek_client.py` — wraps `openai.OpenAI(base_url="https://api.deepseek.com")`
- **Default model:** reuses `LLM_MODEL` setting; recommended value `deepseek-chat`
- **Auth env var:** `DEEPSEEK_API_KEY`
- **Error type caught:** `openai.APIError` → re-raised as `LLMError`

### LLM Provider Selection
- Controlled by `LLM_PROVIDER` env var: `"claude"` (default) or `"deepseek"`
- Factory: `backend/app/infrastructure/ai/factory.py` — `create_llm_client()` returns the correct adapter
- Runtime override: UI settings page writes to `runtime_settings` DB table, overriding env vars per-user
  - See `backend/app/api/v1/settings.py` and `backend/app/application/runtime_settings_service.py`
  - Overridable fields: `llm_provider`, `llm_model`, `anthropic_api_key`, `deepseek_api_key`, `llm_base_url`, `llm_batch_size`, `llm_max_concurrency`

---

## Data Storage

### PostgreSQL 16
- **Type:** Relational database (primary data store)
- **Image:** `postgres:16-alpine` (see `docker-compose.yml`)
- **DB name:** `beancount_bot`
- **Connection env var:** `DATABASE_URL`
  - Default: `postgresql://postgres:postgres@localhost:5432/beancount_bot`
- **ORM/Client:** SQLAlchemy `>=2.0.48` with `psycopg2-binary` sync driver
  - Engine config: `backend/app/infrastructure/persistence/database.py`
  - Pool: `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`
- **Migrations:** Alembic `>=1.18.4`
  - Config: `backend/alembic.ini`
  - Versions: `backend/alembic/versions/` (8 migrations, `001` through `008`)
  - Run: `uv run alembic upgrade head`
- **Tables (from ORM):** `users`, `bill_imports`, `import_stages`, `import_summaries`, `transactions`, `beancount_entries`, `category_rules`, `rule_suggestions`, `monthly_reports`, `budget_plans`, `duplicate_review_groups`, `runtime_settings`

### Redis 7
- **Type:** In-memory key-value store
- **Image:** `redis:7-alpine` (see `docker-compose.yml`)
- **Connection env var:** `REDIS_URL`
  - Default: `redis://redis:6379/0`
- **Uses:**
  - Celery task broker (bill import async jobs)
  - Celery result backend (task state tracking)
- **Client:** `redis` Python package `>=6.4.0` (used transitively via Celery)

---

## File Storage

- **Type:** Local filesystem (no cloud object storage)
- **Volume:** Docker named volume `uploads`, mounted at `/app/uploads` in both `backend` and `worker` containers
- **Env var:** `UPLOAD_DIR` (default: `./uploads`)
- **Usage:** Uploaded bill files are saved to `upload_dir/{import_id}_{filename}` before async processing
- **Reference:** `backend/app/application/import_service.py`

---

## Authentication & Identity

- **Auth provider:** None — MVP single-user mode, no login flow
- **Fixed user:** `DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"` (hardcoded in `backend/app/core/config.py`)
- **Startup behavior:** `backend/app/main.py` calls `ensure_user()` at lifespan start to create the default user if missing
- **No JWT, sessions, OAuth, or API keys** — all requests are implicitly attributed to the single default user

---

## Async Task Queue

- **Broker:** Celery `>=5.6.3` with Redis backend
- **App definition:** `backend/app/infrastructure/queue/celery_app.py`
- **Task module:** `backend/app/infrastructure/queue/import_tasks.py`
- **Queue name:** `imports` — worker subscribes with `-Q imports`
- **Concurrency:** 2 workers (set in `docker-compose.yml` `--concurrency 2`)
- **Timezone:** `Asia/Shanghai` (Celery config)
- **Settings:** `task_acks_late=True`, `worker_prefetch_multiplier=1` (reliable at-least-once delivery)

---

## Bill Parsers (File Format Integrations)

Three bill sources are supported via an adapter registry pattern (`backend/app/infrastructure/parsers/registry.py`):

| Source | Format | Parser File | Key Library |
|--------|--------|-------------|-------------|
| WeChat Pay (`wechat`) | `.xlsx` + CSV | `backend/app/infrastructure/parsers/wechat.py` | `openpyxl` |
| Alipay (`alipay`) | CSV (GBK/GB18030/UTF-8) | `backend/app/infrastructure/parsers/alipay.py` | `chardet` (encoding detection) |
| China Merchants Bank (`cmb`) | PDF | `backend/app/infrastructure/parsers/cmb.py` | `pymupdf` (fitz) + `rapidocr-onnxruntime` (OCR fallback) |

- **Encoding detection:** `chardet` tries multiple encodings: chardet result → `utf-8-sig` → `utf-8` → `gb18030` → `gbk` → `utf-16`
- **PDF extraction:** PyMuPDF `fitz.open()` for embedded text; RapidOCR as fallback for scanned pages
- **Auto-detection:** `registry.auto_detect_file()` tries each registered parser until one claims the file

---

## Frontend to Backend Communication

- **Protocol:** HTTP/REST JSON over internal Docker network (or `localhost` in dev)
- **Base URL:** `NEXT_PUBLIC_API_URL` env var (injected at Next.js build time)
  - Default: `http://localhost:8000/api/v1`
- **Client module:** `frontend/lib/api.ts` — typed wrapper around native `fetch`
- **Data fetching:** SWR `^2.4.1` for cache-backed polling on all pages
- **File upload:** raw `FormData` POST to `/bills/import` (bypasses JSON content-type header)
- **CORS:** FastAPI allows `http://localhost:3000` and `http://127.0.0.1:3000` (`backend/app/main.py`)

---

## Monitoring & Observability

- **Error tracking:** None — no Sentry, Datadog, or equivalent configured
- **Logging:** Python `logging` module only
  - Format: `%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`
  - Level: `INFO` in production, `DEBUG` if `DEBUG=true`
  - Config: `backend/app/core/logging.py`
  - SQLAlchemy engine logs suppressed to `WARNING`
- **Metrics:** None
- **Tracing:** None

---

## CI/CD & Deployment

- **CI pipeline:** None — no `.github/workflows/` directory exists
- **Hosting:** Local Docker Compose only — no cloud deployment config found
- **Image registry:** No remote registry configured
- **Secrets management:** `.env` file at project root (manual — not a secret manager)
  - Template: `.env.example` at project root
  - `make setup` copies `.env.example` → `.env`

---

## Webhooks & Callbacks

- **Incoming webhooks:** None
- **Outgoing webhooks:** None
- **Event system:** In-memory `EventBus` (`backend/app/core/event_bus.py`) — internal only, no external pub/sub

---

## Environment Variables Reference

| Variable | Service | Required | Default | Purpose |
|----------|---------|----------|---------|---------|
| `ANTHROPIC_API_KEY` | backend, worker | Yes (if claude) | — | Claude API auth |
| `DEEPSEEK_API_KEY` | backend, worker | Yes (if deepseek) | — | DeepSeek API auth |
| `LLM_PROVIDER` | backend, worker | No | `claude` | Active LLM provider |
| `LLM_MODEL` | backend, worker | No | `claude-haiku-4-5-20251001` | Model identifier |
| `DATABASE_URL` | backend, worker, migrate | Yes | `postgresql://postgres:postgres@localhost:5432/beancount_bot` | PostgreSQL DSN |
| `REDIS_URL` | backend, worker | Yes | `redis://localhost:6379/0` | Redis DSN |
| `UPLOAD_DIR` | backend, worker | No | `./uploads` | Bill file upload path |
| `DEBUG` | backend | No | `false` | Enable debug logging |
| `NEXT_PUBLIC_API_URL` | frontend (build-time) | No | `http://localhost:8000/api/v1` | Backend API base URL |

---

## Gaps & Unknowns

- No monitoring or error-tracking service — failures are visible only in container logs
- `rapidocr-onnxruntime` may silently fail in Docker if `libxcb1` is not installed; the Dockerfile does not install it
- LLM API keys stored in plaintext in `runtime_settings` DB table — no encryption at rest
- No rate limiting on any endpoint — potential abuse surface if exposed publicly
- No outbound HTTP proxy or retry/backoff configuration for LLM API calls beyond exception catching
