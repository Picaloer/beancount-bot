from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.debug)
    # Ensure default user exists at startup
    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.repositories.transaction_repo import ensure_user
    db = SessionLocal()
    try:
        ensure_user(db, settings.default_user_id)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Beancount Bot API",
    description="AI-powered bill management and Beancount accounting system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.api.v1.bills import router as bills_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.reports import router as reports_router
from app.api.v1.categories import router as categories_router
from app.api.v1.query import router as query_router
from app.api.v1.budgets import router as budgets_router
from app.api.v1.settings import router as settings_router

app.include_router(bills_router, prefix="/api/v1")
app.include_router(transactions_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(query_router, prefix="/api/v1")
app.include_router(budgets_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}
