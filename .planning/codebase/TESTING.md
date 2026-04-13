# Testing Patterns

_Last updated: 2026-04-13_

## Summary

The backend has a growing test suite using pytest with an in-memory SQLite override strategy. Tests are integration-style: they spin up the real FastAPI application against a SQLite `:memory:` database and call HTTP endpoints via `TestClient`. The `backend/tests/` directory contains four test files plus empty `unit/` and `integration/` subdirectories. The frontend has **no test files** — neither unit tests nor E2E tests exist.

---

## Backend

### Test Framework

**Runner:** pytest 9.0.2 + pytest-asyncio 1.3.0

```toml
# backend/pyproject.toml
[dependency-groups]
dev = [
    "httpx>=0.28.1",
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
]
```

No `[tool.pytest.ini_options]` section is present in `pyproject.toml`. No `pytest.ini`, `tox.ini`, or `setup.cfg` files exist.

**Run Commands:**

```bash
# From backend/ directory
cd backend
uv run pytest tests/               # run all tests
uv run pytest tests/test_category_suggestions.py  # single file
uv run pytest tests/ -v            # verbose output
uv run pytest tests/ --cov=app --cov-report=term-missing  # with coverage (pytest-cov not installed)
```

Note: `pytest-cov` is not in `pyproject.toml`; coverage tooling is not set up.

### Test File Organization

**Location:** `backend/tests/` — separate from source, not co-located.

```
backend/tests/
├── conftest.py                        # global env override (SQLite, Redis, API key)
├── test_category_suggestions.py       # API integration: categories + rule suggestions
├── test_bill_parsers.py               # parser smoke tests against real sample files
├── test_import_detail.py              # API integration: import lifecycle & duplicate review
├── test_transaction_deduplication.py  # repository unit: deduplication logic
├── unit/                              # empty
└── integration/                       # empty
```

**Naming:** `test_<feature>.py`. Test functions named `test_<description>` following pytest convention.

### conftest.py Pattern

The conftest overrides environment variables **before** any app module imports:

```python
# backend/tests/conftest.py
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Override DATABASE_URL *before* app imports DB connection
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
```

### Test Structure

All test files share the same setup idiom — create tables on module load and override FastAPI's `get_db` dependency:

```python
# backend/tests/test_category_suggestions.py
from fastapi.testclient import TestClient
from app.main import app as fastapi_app
from app.infrastructure.persistence.database import Base, engine, SessionLocal, get_db
import app.infrastructure.persistence.models.orm_models  # noqa: F401 – register ORM models

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

fastapi_app.dependency_overrides[get_db] = override_get_db
```

### Fixtures

**`autouse=True` table cleanup** — runs between every test to ensure isolation:

```python
@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe all rows between tests."""
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
```

**`scope="module"` TestClient** — shared across tests in a module:

```python
@pytest.fixture(scope="module")
def client():
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c
```

**Helper seed functions** — module-level functions (not fixtures) that insert test data directly via `SessionLocal()`:

```python
def _seed_transaction(merchant="美团外卖", category_l1="餐饮", ...):
    """Insert a minimal transaction and return its id."""
    db = SessionLocal()
    try:
        ensure_user(db, USER_ID)
        imp_id = str(uuid4())
        db.add(BillImportORM(id=imp_id, ...))
        db.flush()
        tx_id = str(uuid4())
        db.add(TransactionORM(id=tx_id, ...))
        db.commit()
        return tx_id
    finally:
        db.close()
```

**Manual cleanup function** (some tests call `_cleanup_tables()` explicitly instead of relying on autouse):

```python
def _cleanup_tables() -> None:
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()
```

### Test Types

**Integration tests (HTTP endpoint tests):**

Tests call real FastAPI endpoints via `TestClient`. They verify HTTP status codes and response bodies. Example from `test_category_suggestions.py`:

```python
def test_create_and_list_rule(client):
    payload = {"match_value": "美团外卖", "category_l1": "餐饮", "category_l2": "外卖",
               "match_field": "merchant", "priority": 10}
    resp = client.post("/api/v1/categories/rules", json=payload)
    assert resp.status_code == 201
    assert resp.json()["match_value"] == "美团外卖"
```

**Repository/domain tests (direct DB layer):**

Tests call repository functions directly using `SessionLocal()`. Example from `test_transaction_deduplication.py`:

```python
def test_bulk_create_transactions_dedupes_cross_source_by_fingerprint():
    _cleanup_tables()
    wechat_import_id = _create_import("wechat")
    ...
    db = SessionLocal()
    try:
        inserted_first = bulk_create_transactions(db, wechat_import_id, USER_ID, [...])
        inserted_second = bulk_create_transactions(db, cmb_import_id, USER_ID, [...])
        assert len(inserted_first) == 1
        assert inserted_second == []
        assert db.query(TransactionORM).count() == 1
    finally:
        db.close()
```

**Parser smoke tests (`test_bill_parsers.py`):**

These tests require real sample bill files present at hardcoded local paths under `backend/uploads/`. They are **not portable** — they will fail on any machine without these files:

```python
PDF_PATH = Path(
    "/home/pica/assets/githubs/beancount-bot/backend/uploads/招商银行交易流水(...).pdf"
)

def test_cmb_pdf_auto_detects_and_parses_transactions():
    parser = auto_detect_file(PDF_PATH)
    assert parser.source_type == "cmb"
    transactions = parser.parse_file(PDF_PATH)
    assert len(transactions) == 227
```

### Mocking

Mocking is done with `pytest`'s `monkeypatch` fixture. Used to stub out side effects:

```python
def test_manual_update_creates_suggestion(client, monkeypatch):
    import app.infrastructure.persistence.repositories.transaction_repo as _repo
    import app.domain.beancount.engine as _engine

    monkeypatch.setattr(_repo, "save_beancount_entry", lambda *a, **kw: None)

    class _FakeEntry:
        date = "2026-01-15"
        postings = []
        def render(self): return ""

    monkeypatch.setattr(_engine.BeancountEngine, "generate_entry",
                        lambda self, tx: _FakeEntry())
```

No `unittest.mock`, `MagicMock`, or external mocking libraries are used.

### Assertions Pattern

Plain `assert` statements throughout (no assertion library). HTTP tests assert `status_code` then `response.json()` fields:

```python
assert resp.status_code == 201
assert resp.json()["match_value"] == "美团外卖"
assert resp.json()["status"] == "pending"
assert abs(resp.json()["confidence"] - 0.92) < 0.001  # float comparison
```

### Coverage

No coverage tool is configured. `pytest-cov` is not in `pyproject.toml`. The `.gitignore` includes `.coverage`, suggesting coverage runs have been attempted manually but are not integrated.

```
# .gitignore
.pytest_cache/
.coverage
```

**Estimated coverage:** The four test files together cover:
- `app/api/v1/categories.py` — heavily covered
- `app/api/v1/bills.py` — partially covered (import, delete, duplicate review endpoints)
- `app/api/v1/transactions.py` — partially covered (category update)
- `app/infrastructure/persistence/repositories/transaction_repo.py` — partially covered
- `app/infrastructure/parsers/` — smoke-tested (file-path dependent)
- `app/application/import_service.py`, `app/domain/`, `app/infrastructure/ai/` — **not tested**

---

## Frontend

### Test Status

**No tests exist.** There are no test files, no test framework installed (Jest, Vitest, Playwright are absent from `frontend/package.json`), and no `test` script in `package.json`:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  }
}
```

Playwright is present in `pnpm-lock.yaml` as an optional dependency of `eslint-config-next`, not as a direct test dependency. No Playwright config file (`playwright.config.ts`) exists.

---

## CI/CD

No `.github/workflows/` directory exists. There is no CI pipeline. Tests must be run locally.

---

## Running Tests Locally

**Backend:**

```bash
cd /home/pica/assets/githubs/beancount-bot/backend
uv run pytest tests/ -v
```

**Note:** `test_bill_parsers.py` requires real sample bill files at:
- `backend/uploads/招商银行交易流水(...).pdf`
- `backend/uploads/微信支付账单流水文件(...).xlsx`
- `backend/uploads/支付宝交易明细(...).csv`

Skip that file if sample data is not present:

```bash
uv run pytest tests/ -v --ignore=tests/test_bill_parsers.py
```

---

## Gaps & Unknowns

1. **No frontend tests at all** — all UI behaviour (React components, SWR hooks, form handling, page navigation) is untested.
2. **No E2E tests** — critical user flows (upload bill, duplicate review, category override) have zero automated coverage.
3. **Coverage not measured** — `pytest-cov` is not installed; 80% coverage goal cannot be verified.
4. **Parser tests are non-portable** — `test_bill_parsers.py` depends on absolute local file paths. Any contributor without the exact sample files will get `FileNotFoundError`.
5. **`unit/` and `integration/` subdirectories are empty** — scaffolded but never populated.
6. **No async test coverage** — `pytest-asyncio` is installed but no `@pytest.mark.asyncio` tests exist. Celery tasks and async AI calls are untested.
7. **No `pytest.ini_options`** — asyncio mode, test discovery paths, and markers are not configured in `pyproject.toml`.
8. **No database migration tests** — Alembic migrations are not tested for correctness (up/down).
