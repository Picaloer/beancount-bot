"""
Pytest configuration: wire an in-memory SQLite engine before any app module
imports its database connection, so tests never touch the real Postgres DB.
"""
import os
import sys
from pathlib import Path

# ── put project root on sys.path ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── override DATABASE_URL *before* any app code is imported ──────────────────
# pydantic-settings reads from .env; setting it here wins over the file.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
