# Concerns & Risks
_Last updated: 2026-04-13_

## Summary

Beancount Bot is an MVP-stage personal finance tool in a single-user mode with no authentication. The overall code quality is good — clean architecture, proper ORM usage, no raw SQL injection surface, structured error handling. The primary risks are: (1) complete absence of authentication/authorization which would require a significant architectural addition to multi-user scenarios, (2) a single large repository file that has grown to 1,113 lines and handles heterogeneous concerns, and (3) shallow test coverage with no unit tests for core domain logic or API routes.

---

## Security Concerns

### HIGH — No Authentication or Authorization on Any Endpoint
- **All API endpoints** are fully open and unauthenticated
- `settings.default_user_id` (`"00000000-0000-0000-0000-000000000001"`) is hardcoded as a constant in `backend/app/core/config.py:30` and used everywhere across all seven router files
- Any network-accessible instance exposes all financial data and LLM API keys stored in `runtime_settings` to unauthenticated callers
- Files: `backend/app/core/config.py:30`, every file in `backend/app/api/v1/`
- Current mitigation: Docker CORS limited to `localhost:3000` (`backend/app/main.py:33`)
- Fix approach: This is an intentional MVP design decision; adding auth requires JWT middleware, user extraction from token, and passing `user_id` from request context rather than from the config constant

### HIGH — LLM API Keys Stored in Database Unencrypted
- `RuntimeSettingORM.anthropic_api_key` and `RuntimeSettingORM.deepseek_api_key` are stored as plaintext `Text` columns in PostgreSQL
- Files: `backend/app/infrastructure/persistence/models/orm_models.py:100-101`
- The `GET /settings/runtime` endpoint masks keys in responses (`backend/app/api/v1/settings.py:41-47`), but the underlying DB value is plaintext
- A DB dump or direct DB access exposes all API keys
- Fix approach: Encrypt at rest using Fernet symmetric encryption before persisting, or use a secrets manager

### MEDIUM — No File Upload Size Limit
- `POST /api/v1/bills/import` accepts any file with no size validation
- The entire file content is read into memory synchronously: `content = file.file.read()` in `backend/app/api/v1/bills.py:25`
- A large file can exhaust FastAPI worker memory
- Fix approach: Add `Content-Length` check or stream with size limit via FastAPI `UploadFile` constraints

### MEDIUM — No File Type Validation on Upload
- Only the file extension and content signature are checked by parser registry auto-detection (`backend/app/infrastructure/parsers/registry.py`)
- The API layer does not validate `Content-Type` or extension before saving the file to disk
- Attacker can upload arbitrary bytes; they will fail at parser detection but the file is saved to disk first in `backend/app/application/import_service.py:29`
- Fix approach: Validate extension allowlist (`.csv`, `.xlsx`, `.pdf`) and `Content-Type` header in the route before saving

### MEDIUM — CORS Only Restricts Origins, Not Full CSRF Protection
- CORS is set to `localhost:3000` and `127.0.0.1:3000` (`backend/app/main.py:33`) with `allow_credentials=True`
- There is no CSRF token mechanism; since there is no session/cookie auth currently this is not exploitable, but becomes relevant if cookie-based auth is added later

### LOW — `assert` Used for Input Validation in API Routes
- `assert` statements are used for input validation inside request handlers, which raises `AssertionError` (500 Internal Server Error) rather than a clean 400
- Files: `backend/app/api/v1/reports.py:23`, `backend/app/api/v1/reports.py:93`, `backend/app/api/v1/budgets.py:20`
- Example: `assert len(year) == 4 and 1 <= int(month) <= 12` — Python's `-O` flag silently disables all asserts
- Fix approach: Replace with explicit `HTTPException(status_code=400, ...)` raises

---

## Technical Debt

### `transaction_repo.py` Has Grown to 1,113 Lines with Mixed Concerns
- `backend/app/infrastructure/persistence/repositories/transaction_repo.py` is 1,113 lines — the single largest file, well above the 800-line guideline
- It handles: user creation, import lifecycle, stage management, duplicate review, transaction CRUD, rule suggestions, budget plans, beancount entries, category trends, and monthly stats
- This violates single-responsibility and makes the file hard to navigate
- Fix approach: Split into focused repositories — `ImportRepository`, `TransactionRepository`, `RuleRepository`, `BudgetRepository`, `ReportRepository`

### In-Process Classification Continuation Runs Synchronously in Request Cycle
- `resolve_duplicate_review_group` in `backend/app/application/import_service.py:93` calls `resume_import_after_duplicate_review` synchronously on the HTTP request thread
- `resume_import_after_duplicate_review` runs the full classification and Beancount generation pipeline, which can take minutes for large imports
- This can cause a request timeout or block a worker thread
- Fix approach: Dispatch to Celery: `resume_import_after_duplicate_review.delay(import_id, user_id)` instead of the synchronous call

### `list_available_months` Uses PostgreSQL-Specific `func.to_char`
- `backend/app/application/report_service.py:84-88` uses `func.to_char(TransactionORM.transaction_at, "YYYY-MM")` which is PostgreSQL-only
- Tests run against SQLite (`backend/tests/conftest.py:16`) so this path is never exercised in tests
- This creates a silent testing gap: the test DB and production DB behavior diverge for this query
- Fix approach: Use SQLAlchemy `extract` or format in Python after fetching dates

### Inline SQL-Like Logic in Route Handler (`list_imports`)
- `backend/app/api/v1/bills.py:95-129` — the `list_imports` route contains inline SQLAlchemy query and serialization logic instead of delegating to the service/repository layer
- Hard-coded `.limit(20)` with no pagination
- Fix approach: Move to `import_service.list_imports()` and add proper pagination support

### `update_import_status` Has 13 Optional Parameters
- `backend/app/infrastructure/persistence/repositories/transaction_repo.py:59-74` — this function signature has 13 keyword-only parameters, making call sites verbose and error-prone
- Called throughout `import_tasks.py` with different parameter combinations
- Fix approach: Use a dataclass or TypedDict for the update payload

---

## Performance Risks

### `get_monthly_stats` Loads All Transactions into Memory
- `backend/app/infrastructure/persistence/repositories/transaction_repo.py:923-981` fetches all transactions for a month into Python memory, then aggregates in Python loops
- With large transaction volumes (thousands of rows per month), this is inefficient
- The function is called twice per report generation: once for the current month, once for the previous month (`backend/app/application/report_service.py:29,44`)
- Fix approach: Perform aggregation in the DB using `GROUP BY` queries with `SUM`/`COUNT`

### `get_category_trends` Fetches All Transactions for 6-Month Window
- `backend/app/infrastructure/persistence/repositories/transaction_repo.py:984-1048` loads all expense transactions for up to 6 months into Python memory for aggregation
- Same pattern as `get_monthly_stats` — should use DB-side aggregation
- Files: `backend/app/infrastructure/persistence/repositories/transaction_repo.py:997-1006`

### `generate_rule_suggestions_from_history` Loads All Classified Transactions
- `backend/app/infrastructure/persistence/repositories/transaction_repo.py:642-731` fetches all LLM/manual-classified transactions for the user with no pagination or limit
- This becomes a full table scan as the transaction history grows
- Files: `backend/app/infrastructure/persistence/repositories/transaction_repo.py:649-655`

### LLM Classification Uses `ThreadPoolExecutor` Sharing a Synchronous DB Session
- `backend/app/domain/classification/batch_runner.py:82-106` uses `ThreadPoolExecutor` for concurrent LLM calls
- The `on_progress` callback in `backend/app/infrastructure/queue/import_tasks.py:335-349` accesses a SQLAlchemy `Session` from the worker thread via closure capture
- SQLAlchemy sessions are not thread-safe; concurrent writes from the progress callback and main thread can cause intermittent failures
- Fix approach: Use a thread-local session or pass DB write operations through a queue

### Monthly Report Generation Blocks on LLM Call During HTTP Request
- `backend/app/application/report_service.py:33-52` calls the AI insight agent synchronously during `GET /reports/monthly/{year_month}`
- If the LLM provider is slow or unavailable, the HTTP request hangs until timeout
- The `try/except` catches failures gracefully, but the wait still blocks the caller
- Fix approach: Generate AI insights as a background task; return cached stats immediately with `ai_insight: null` and update later

---

## Reliability Gaps

### Celery Task Retry Storm on Classification Failure
- `backend/app/infrastructure/queue/import_tasks.py:223` — `raise self.retry(exc=exc, countdown=30)` with `max_retries=3` retries the **entire** import pipeline on any failure
- If failure occurs mid-pipeline (e.g., after file is parsed and transactions are inserted), the retry will re-run `bulk_create_transactions` against already-inserted records
- Deduplication logic should prevent duplicate rows, but stage state is reset to failed (`status="failed"`) then re-run from the start
- Fix approach: Break the pipeline into idempotent Celery sub-tasks per stage

### Uploaded Files Are Never Cleaned Up on Worker Success
- `backend/app/application/import_service.py:108-110` deletes the uploaded file only when `delete_import` is called explicitly
- Files processed by the worker remain in `uploads/` indefinitely after successful import
- On disk-constrained deployments this accumulates unboundedly
- Fix approach: Delete or archive the upload file at the end of `_continue_import_after_duplicate_review`

### `resume_import_after_duplicate_review` Has No Error Handling
- `backend/app/infrastructure/queue/import_tasks.py:228-246` — classification failure inside `_continue_import_after_duplicate_review` bubbles up as an unhandled exception; it does not update the import status to `"failed"` or any error state
- Unlike the Celery task which has a broad `try/except`, this synchronous code path has none
- Fix approach: Wrap the continuation call with the same error-handling pattern used in `process_bill_import`

### No Health Check for Database or Redis in Backend Startup
- `backend/app/main.py` `lifespan` handler only ensures a user record exists; it does not verify DB connectivity or Redis/Celery availability
- If Postgres or Redis goes down after startup, the API returns 500 errors with no diagnostic information in the `/health` endpoint
- Fix approach: Extend `GET /health` to check DB and Redis reachability

### Single Celery Worker with Fixed Concurrency
- `docker-compose.yml:89` starts a single Celery worker with `--concurrency 2`
- There is no horizontal scaling configuration or dead-letter queue for permanently failed tasks
- Fix approach: Add `task_reject_on_worker_lost = True` and configure a dead-letter queue

---

## Maintainability Issues

### Test Coverage for Core Domain Logic Is Absent
- `backend/tests/unit/` and `backend/tests/integration/` directories both exist but are completely empty
- Coverage areas with no tests:
  - `backend/app/domain/classification/pipeline.py` — the 4-stage classification pipeline
  - `backend/app/domain/classification/rule_engine.py` — rule matching logic
  - `backend/app/domain/beancount/engine.py` — Beancount entry generation
  - `backend/app/domain/classification/batch_runner.py` — concurrent LLM batch runner
  - All API routes (no route-level tests; only repository-level tests exist)
- The only integration tests are `test_import_detail.py`, `test_transaction_deduplication.py`, `test_category_suggestions.py`, and `test_bill_parsers.py`
- `test_bill_parsers.py` relies on actual files at hardcoded absolute paths (`/home/pica/assets/...`) — tests will fail on any other machine

### `test_bill_parsers.py` References Absolute Paths to Personal Files
- `backend/tests/test_bill_parsers.py:12-20` — PDF and XLSX paths are hardcoded to a developer's local filesystem
- These tests cannot run in CI or on any other machine without the specific files
- Fix approach: Either commit sample fixtures or skip with `pytest.mark.skipif`

### No Frontend Tests Exist
- The entire `frontend/` application (Next.js + TypeScript) has no test files outside of `node_modules`
- No Playwright E2E tests, no Jest/Vitest unit tests for UI components or `lib/api.ts`
- Fix approach: Add Vitest unit tests for `frontend/lib/api.ts` and Playwright E2E for critical import/review flows

### Status Strings Are Untyped Magic Strings Throughout Backend
- Import lifecycle statuses (`"pending"`, `"processing"`, `"reviewing_duplicates"`, `"classifying"`, `"done"`, `"failed"`) are plain strings in `BillImportORM.status`, not an Enum
- Stage statuses (`"pending"`, `"processing"`, `"done"`, `"failed"`) have the same issue
- This creates risk of typos with no static analysis protection
- Files: `backend/app/infrastructure/persistence/models/orm_models.py:39`, throughout `import_tasks.py`
- Fix approach: Add `enum.StrEnum` types for import and stage status values

### `_continue_import_after_duplicate_review` Is a 230-Line Function
- `backend/app/infrastructure/queue/import_tasks.py:249-487` — single function handling: transaction loading, duplicate review finalization, LLM classification, Beancount generation, and all DB updates
- Violates the <50-line function guideline significantly
- Fix approach: Extract `_run_classification_phase`, `_run_beancount_phase` as standalone functions

---

## Dependency Risks

### `rapidocr-onnxruntime` Has System Dependency (`libxcb1`)
- `backend/app/infrastructure/parsers/cmb.py:103-108` — OCR fallback requires `libxcb1` system library which may not be present in all Docker base images
- The current Docker image uses `python:3.13-slim`; `libxcb1` is not pre-installed
- If OCR path is triggered on a scanned PDF, the import fails with `RuntimeError`
- Fix approach: Either install `libxcb1` in the Dockerfile or document the limitation clearly

### `func.to_char` Ties the Application to PostgreSQL
- `backend/app/application/report_service.py:84` — the `list_available_months` function is permanently tied to PostgreSQL dialect
- The `conftest.py` test override to SQLite means this code path is **never tested** in CI
- Fix approach: Replace with dialect-agnostic string formatting

### `openai>=1.0.0` Is Listed as a Dependency but Not Used
- `backend/pyproject.toml:9` includes `openai>=1.0.0` as a direct dependency
- No import of `openai` was found in the application source; `DeepSeekClient` uses `anthropic.Anthropic` with a custom `base_url`
- This adds unnecessary package weight and a potential vulnerability surface
- Fix approach: Remove `openai` from `pyproject.toml`; if DeepSeek OpenAI compatibility is needed, import conditionally or use `httpx` directly

### `pypdf` and `pymupdf` Are Both Listed for PDF Handling
- `backend/pyproject.toml:22-23` includes both `pypdf` and `pymupdf`
- Only `pymupdf` (`fitz`) is actually used in `backend/app/infrastructure/parsers/cmb.py`
- `pypdf` appears unused (no import found in app code)
- Fix approach: Remove `pypdf` from dependencies

### No Dependency Pinning Beyond Lower Bounds
- All dependencies in `pyproject.toml` use `>=` lower bounds with no upper bounds
- A breaking release of any dependency (e.g., `sqlalchemy>=3.0`, `fastapi>=1.0`) could silently break the build
- The `uv.lock` lockfile mitigates this for reproducible builds, but the manifest itself does not express intent
- Fix approach: Pin major versions with `>=X.Y,<X+1` bounds for critical dependencies

---

## Gaps & Unknowns

- **Alembic migration state**: The migration history in `backend/alembic/versions/` was not inspected — it is unknown whether the schema migrations are complete, ordered, and correct relative to ORM models
- **Frontend error states**: React component error boundaries and loading states were not inspected; it is unknown whether all API error cases are handled gracefully in the UI
- **Celery flower / monitoring**: No monitoring or observability for the Celery queue is configured — it is unknown whether tasks are being retried silently or accumulating in the queue
- **LLM cost guardrails**: There is no token budget limit or circuit-breaker for the LLM classification pipeline; a pathologically large import could incur unexpected API costs
- **Database index coverage**: Only `transaction_at`, `external_id`, and `dedupe_key` columns are explicitly indexed on `TransactionORM`; queries filtering by `category_l1`, `direction`, or `import_id` may perform full table scans at scale
