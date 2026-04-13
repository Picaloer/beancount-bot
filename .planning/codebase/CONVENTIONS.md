# Coding Conventions

_Last updated: 2026-04-13_

## Summary

This is a full-stack project: a Python 3.13 FastAPI backend and a Next.js 16 / TypeScript frontend. The backend follows clean-architecture layering with strict type annotations and Python stdlib `logging`. The frontend uses React 19 server/client components, Tailwind CSS 4, and a thin fetch-based API layer. Neither side has automated formatters enforced in CI; formatting expectations come from the team's global developer rules (black/ruff for Python, Prettier for TypeScript).

---

## Backend (Python)

### Naming Patterns

**Files:**
- Module names: `snake_case` — `import_service.py`, `transaction_repo.py`, `claude_client.py`
- ORM model files: `orm_models.py` (all models in one file per layer)
- Test files: `test_<feature>.py` — `test_category_suggestions.py`, `test_import_detail.py`

**Classes:**
- PascalCase: `BillParserAdapter`, `ClassificationPipeline`, `TransactionORM`, `BeancountEngine`
- ORM classes suffixed with `ORM`: `TransactionORM`, `BillImportORM`, `CategoryRuleORM`
- Domain dataclasses unsuffixed: `RawTransaction`, `Transaction`, `ClassificationResult`
- ABC base classes: `BillParserAdapter(ABC)`, `ClassificationStage(ABC)`, `AIAgent(ABC)`

**Functions:**
- `snake_case`: `submit_import`, `bulk_create_transactions`, `auto_detect_file`, `setup_logging`
- Private helpers prefixed with `_`: `_serialize`, `_read_text_candidates`, `_normalize_dedupe_text`
- Module-level logger: `logger = logging.getLogger(__name__)` at top of each module that needs logging

**Variables:**
- `snake_case` throughout
- Constants: `UPPERCASE` — `SYSTEM_RULES`, `USER_ID` in tests
- Enum values: lowercase strings matching domain vocabulary — `"expense"`, `"wechat"`, `"user_rule"`

**Enums:**
- All enums inherit from both `str` and `Enum`: `class TransactionDirection(str, Enum)`
- Values are lowercase strings: `EXPENSE = "expense"`, `WECHAT = "wechat"`

### Type Annotations

Type annotations are present on **all** function signatures. The codebase uses Python 3.10+ union syntax (`X | None`, `list[str]`, `dict[str, Any]`) throughout:

```python
# backend/app/domain/transaction/models.py
def build_transaction_dedupe_key(
    *,
    direction: TransactionDirection,
    amount: float,
    currency: str,
    merchant: str,
    description: str,
    transaction_at: datetime,
) -> str:
```

```python
# backend/app/application/import_service.py
def submit_import(db: Session, file_content: bytes, file_name: str, user_id: str) -> dict:
```

SQLAlchemy ORM models use `Mapped[T]` annotations with `mapped_column`:

```python
# backend/app/infrastructure/persistence/models/orm_models.py
id: Mapped[str] = mapped_column(String(36), primary_key=True)
status: Mapped[str] = mapped_column(String(32), default="pending")
category_l2: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

### Import Organization

Backend imports follow this order (no isort config found; pattern inferred):

1. Standard library (`os`, `logging`, `pathlib`, `uuid`, `datetime`, `json`, `abc`)
2. Third-party (`fastapi`, `sqlalchemy`, `pydantic`, `celery`, `anthropic`)
3. Internal — core first, then domain, then infrastructure: `from app.core.config import settings`

Deferred / local imports are used to break circular dependencies:

```python
# backend/app/domain/classification/pipeline.py
if TYPE_CHECKING:
    from app.domain.classification.rule_engine import Rule, RuleEngine

class UserDefinedRuleStage(ClassificationStage):
    def __init__(self, user_rules: list | None = None) -> None:
        from app.domain.classification.rule_engine import RuleEngine  # local import
```

### Error Handling

**Domain errors** — raised as custom exceptions, defined in `backend/app/core/exceptions.py`:

```python
class BeancountBotError(Exception): ...
class UnsupportedFormatError(BeancountBotError): ...
class ParseError(BeancountBotError): ...
class ClassificationError(BeancountBotError): ...
class LLMError(BeancountBotError): ...
class ImportNotFoundError(NotFoundError): ...
class TransactionNotFoundError(NotFoundError): ...
```

**API layer** — domain exceptions are caught and converted to `HTTPException`:

```python
# backend/app/api/v1/bills.py
except ParseError as e:
    raise HTTPException(status_code=422, detail=str(e))
except ImportNotFoundError as e:
    raise HTTPException(status_code=404, detail=str(e)) from e
```

**Repository layer** — uses `ValueError` for business constraint violations:

```python
raise ValueError("Duplicate review group not found")
raise ValueError("Import is not waiting for duplicate review")
raise ValueError("match_value cannot be empty")
```

**Service/agent layer** — logs and absorbs optional failures, never silently swallows errors for required paths:

```python
except Exception as e:
    logger.warning("Insight generation skipped: %s", e)
```

### Logging

- Setup: `backend/app/core/logging.py` — single `setup_logging(debug: bool)` call at startup
- Format: `"%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"` to `sys.stdout`
- Module loggers: `logger = logging.getLogger(__name__)` at module level
- Log call style: `%`-style formatting (never f-strings in log calls):
  ```python
  logger.warning("Failed to refresh Beancount entry for %s: %s", transaction_id, exc)
  logger.error("Claude API error: %s", e)
  ```
- Library silencing: SQLAlchemy engine at WARNING; httpx at WARNING; celery at INFO

### Comments and Docstrings

- Module docstrings: short one-liner or brief explanatory block at the top of complex modules:
  ```python
  # backend/app/domain/transaction/models.py
  """
  Pure domain models (no ORM dependency).
  These are the canonical objects passed between layers.
  """
  ```
- Inline comments: used for context that the code alone doesn't convey — `# Quiet noisy libraries`, `# noqa: F401 – register ORM models`
- Function-level docstrings: present on public API endpoints and key service methods:
  ```python
  def list_transactions(...):
      """List transactions with optional filters."""
  ```
- No JSDoc/Sphinx-style docstrings in the codebase.

### Data Modeling

Domain objects are `@dataclass`:

```python
@dataclass
class RawTransaction:
    source: BillSource
    direction: TransactionDirection
    amount: float
    ...
    raw_data: dict[str, Any] = field(default_factory=dict)
    external_id: str | None = None
```

Frozen dataclasses are not used in production code (only in tests). `AgentResult` uses a plain `@dataclass` in `backend/app/infrastructure/ai/agents/base.py`.

Settings use `pydantic-settings`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    database_url: str = "postgresql://postgres:postgres@localhost:5432/beancount_bot"
```

### Architecture Conventions

- Layers are enforced by import direction: `api` → `application` → `domain` (no framework imports). Infrastructure adapts domain abstractions.
- Registry pattern for parsers: `register(parser)` → `auto_detect_file(path)`.
- ABC base classes define contracts: `BillParserAdapter(ABC)`, `ClassificationStage(ABC)`, `AIAgent(ABC)`.
- Chain of Responsibility for classification: `UserDefinedRuleStage → SystemRuleStage → LLMStage → FallbackStage`.
- Dependency injection at API level via FastAPI `Depends(get_db)`.
- Single-user MVP: `settings.default_user_id = "00000000-0000-0000-0000-000000000001"` used everywhere in lieu of auth.

---

## Frontend (TypeScript / React)

### Naming Patterns

**Files:**
- Next.js pages: `page.tsx` in feature directories — `app/import/page.tsx`, `app/reports/[yearMonth]/page.tsx`
- Shared components: `PascalCase.tsx` — `Badge.tsx`, `Card.tsx`, `EmptyState.tsx`, `PageHeader.tsx`
- API layer: `lib/api.ts` (single file)
- Dynamic route segments: `[paramName]` directory convention — `app/import/[importId]/page.tsx`

**Components:**
- PascalCase, named exports for reusable components: `export function SourceBadge(...)`, `export default function Card(...)`
- Sub-components (local to a page file) are defined as plain functions in the same file: `function MetricChip(...)`, `function ImportProgress(...)`, `function MessageCard(...)`

**Types and Interfaces:**
- All API response types declared as `export interface` in `lib/api.ts`
- Props typed inline (no separate `*Props` type files): `{ children: ReactNode; className?: string; variant?: CardVariant }`
- String literal unions preferred over enums: `"surface" | "elevated" | "bordered"`, `"expense" | "income" | "transfer"`
- `type` aliases for unions: `export type CardVariant = "surface" | "elevated" | "bordered"`, `export type ImportLifecycleStatus = ...`

**Functions:**
- `camelCase` for all functions and event handlers: `handleFile`, `handleDelete`, `onDrop`, `formatImportTime`
- Boolean helpers: named `canXxx` / `isXxx`: `canDeleteImport`, `isTerminalStatus`
- Utility functions at file bottom: `formatImportTime`, `formatNumber`, `sourceLabel`, `calculateProgress`

**Variables:**
- `camelCase`: `fileRef`, `statusData`, `primaryButtonClassName`
- Constants (module-level strings): `camelCase` with `const`: `primaryButtonClassName`, `secondaryButtonClassName`

### TypeScript Usage

`tsconfig.json` has `"strict": true`. Practices observed:

- `unknown` used for caught errors, narrowed with `instanceof Error`:
  ```typescript
  } catch (e: unknown) {
    setError(e instanceof Error ? e.message : "上传失败");
  }
  ```
- No `any` in production code
- Props types are inline object types on function parameters (no separate `interface FooProps`)
- `React.FC` not used; plain function components with explicit props typing
- `void` used to explicitly discard floating promises: `void handleFile(file)`, `void mutateImports()`

### Import Organization

1. React / Next.js core: `import { useRef, useState } from "react"`, `import Link from "next/link"`
2. Third-party: `import useSWR from "swr"`
3. Project components (`@/app/components/...`)
4. Project lib (`@/lib/api`)
5. Types (inline with imports, using `type` keyword)

Path alias: `@/*` maps to the project root (configured in `tsconfig.json`).

### API Layer Pattern

All API calls go through `lib/api.ts`. The `request<T>()` helper centralises fetch, error handling, and JSON parsing:

```typescript
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  } catch {
    throw new Error("无法连接到后端服务，请确认 API 服务已启动");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}
```

All data types (`ImportStatus`, `Transaction`, `MonthlyReport`, etc.) are co-located in the same file at the bottom.

### Error Handling (Frontend)

- Component-level error state: `const [error, setError] = useState<string | null>(null)`
- Always clear error before async operation: `setError(null)`
- Narrow caught `unknown`: `e instanceof Error ? e.message : "fallback message"`
- Never use `console.log` in production code; no `console.*` calls found in application source

### State and Data Fetching

- SWR for server state: `useSWR(key, fetcher, options)` — polling interval controlled by data:
  ```typescript
  useSWR("imports", listImports, {
    refreshInterval: (records) =>
      records?.some((record) => !isTerminalStatus(record.status)) ? 2000 : 0,
  })
  ```
- Local UI state: `useState` for loading flags, selection state, error messages
- `useRef` for DOM references (file input)

### Styling

- Tailwind CSS 4 utility classes throughout
- CSS custom properties for design tokens: `var(--gold-400)`, `var(--text-primary)`, `var(--bg-surface)`, `var(--border-default)`
- `cx(...)` utility from `Card.tsx` for conditional class joining (no external library like `clsx`):
  ```typescript
  export function cx(...parts: Array<string | false | null | undefined>) {
    return parts.filter(Boolean).join(" ");
  }
  ```
- Inline Tailwind arbitrary values widely used: `bg-[rgba(212,168,67,0.08)]`, `rounded-[28px]`

### Component Conventions

- `"use client"` directive on all interactive page components
- Default export for pages, named exports for reusable shared components
- SVG icons defined as inline function components at the bottom of the file using them: `function UploadGlyph({ className })`
- Component props: `className?: string` accepted by all reusable components for composability
- Variant maps for badges/cards use `Record<string, string>` rather than switch statements

---

## Gaps & Unknowns

- No `ruff.toml`, `pyproject.toml` `[tool.ruff]` section, `.flake8`, or `mypy.ini` found — linting/formatting rules are not enforced in the repo configuration (relies on developer's global tools).
- No Prettier config (`.prettierrc`, `prettier.config.*`) in `frontend/` — formatting is not auto-enforced in repo.
- No `[tool.pytest.ini_options]` section in `pyproject.toml` — pytest options (asyncio mode, test paths) must be passed on the command line or are absent.
- Some functions in the API layer have inline imports (`from sqlalchemy import select`) rather than top-level imports; this is inconsistent and may indicate refactoring backlog.
