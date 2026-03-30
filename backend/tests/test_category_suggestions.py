"""
Tests for the rule-suggestion feedback loop:
  - POST /api/v1/categories/rules
  - GET  /api/v1/categories/rules
  - DELETE /api/v1/categories/rules/{id}
  - GET  /api/v1/categories/rule-suggestions
  - POST /api/v1/categories/rule-suggestions
  - POST /api/v1/categories/rule-suggestions/generate
  - POST /api/v1/categories/rule-suggestions/{id}/approve
  - POST /api/v1/categories/rule-suggestions/{id}/reject
  - PATCH /api/v1/transactions/{id}/category  (creates pending suggestion)
"""
import pytest
from fastapi.testclient import TestClient

# ── app + DB imports (conftest.py already set DATABASE_URL=sqlite:///:memory:)
from app.main import app as fastapi_app
from app.infrastructure.persistence.database import Base, engine, SessionLocal, get_db
import app.infrastructure.persistence.models.orm_models  # noqa: F401 – register ORM models

# Create all tables once for this test module
Base.metadata.create_all(bind=engine)


# ── dependency override: each test gets its own session from the same engine ─
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = override_get_db


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe all rows between tests."""
    yield
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture(scope="module")
def client():
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c


# ── helpers ──────────────────────────────────────────────────────────────────

from app.core.config import settings
USER_ID = settings.default_user_id


def _seed_transaction(merchant="美团外卖", category_l1="餐饮", category_l2="外卖",
                      category_source="llm", confidence=0.9):
    """Insert a minimal transaction and return its id."""
    from uuid import uuid4
    from datetime import datetime
    from app.infrastructure.persistence.models.orm_models import BillImportORM, TransactionORM
    from app.infrastructure.persistence.repositories.transaction_repo import ensure_user

    db = SessionLocal()
    try:
        ensure_user(db, USER_ID)

        imp_id = str(uuid4())
        db.add(BillImportORM(
            id=imp_id, user_id=USER_ID, source="wechat",
            file_name="test.xlsx", status="done",
        ))
        db.flush()

        tx_id = str(uuid4())
        db.add(TransactionORM(
            id=tx_id, user_id=USER_ID, import_id=imp_id,
            source="wechat", direction="expense",
            amount=38.5, currency="CNY",
            merchant=merchant, description="测试交易",
            category_l1=category_l1, category_l2=category_l2,
            category_source=category_source, category_confidence=confidence,
            transaction_at=datetime(2026, 1, 15, 12, 0),
        ))
        db.commit()
        return tx_id
    finally:
        db.close()


# ── Category tree ─────────────────────────────────────────────────────────────

def test_get_category_tree(client):
    resp = client.get("/api/v1/categories")
    assert resp.status_code == 200
    l1_names = [item["category_l1"] for item in resp.json()["tree"]]
    assert "餐饮" in l1_names
    assert "购物" in l1_names


# ── Rules CRUD ───────────────────────────────────────────────────────────────

def test_create_and_list_rule(client):
    payload = {
        "match_value": "美团外卖",
        "category_l1": "餐饮",
        "category_l2": "外卖",
        "match_field": "merchant",
        "priority": 10,
    }
    resp = client.post("/api/v1/categories/rules", json=payload)
    assert resp.status_code == 201
    rule = resp.json()
    assert rule["match_value"] == "美团外卖"
    assert rule["id"]

    rules = client.get("/api/v1/categories/rules").json()
    assert any(r["match_value"] == "美团外卖" for r in rules)


def test_create_rule_invalid_l1(client):
    resp = client.post("/api/v1/categories/rules",
                       json={"match_value": "test", "category_l1": "不存在的分类"})
    assert resp.status_code == 400


def test_create_rule_invalid_l2(client):
    resp = client.post("/api/v1/categories/rules",
                       json={"match_value": "test", "category_l1": "餐饮", "category_l2": "汽车"})
    assert resp.status_code == 400


def test_delete_rule(client):
    rule_id = client.post("/api/v1/categories/rules", json={
        "match_value": "要删除的商户", "category_l1": "餐饮", "category_l2": "外卖",
    }).json()["id"]

    assert client.delete(f"/api/v1/categories/rules/{rule_id}").status_code == 204
    rules = client.get("/api/v1/categories/rules").json()
    assert not any(r["id"] == rule_id for r in rules)


# ── Rule Suggestions CRUD ────────────────────────────────────────────────────

def test_list_suggestions_initially_empty(client):
    assert client.get("/api/v1/categories/rule-suggestions").json() == []


def test_create_suggestion(client):
    payload = {
        "match_value": "瑞幸咖啡",
        "category_l1": "餐饮",
        "category_l2": "咖啡",
        "confidence": 0.92,
        "source": "llm_feedback",
    }
    resp = client.post("/api/v1/categories/rule-suggestions", json=payload)
    assert resp.status_code == 201
    s = resp.json()
    assert s["match_value"] == "瑞幸咖啡"
    assert s["status"] == "pending"
    assert abs(s["confidence"] - 0.92) < 0.001


def test_create_suggestion_deduplication(client):
    """Same merchant+category twice → single updated record."""
    payload = {"match_value": "星巴克", "category_l1": "餐饮",
               "category_l2": "咖啡", "confidence": 0.85, "source": "llm_feedback"}
    id1 = client.post("/api/v1/categories/rule-suggestions", json=payload).json()["id"]

    payload2 = {**payload, "confidence": 0.95}
    resp2 = client.post("/api/v1/categories/rule-suggestions", json=payload2)
    assert resp2.json()["id"] == id1
    assert abs(resp2.json()["confidence"] - 0.95) < 0.001

    pending = client.get("/api/v1/categories/rule-suggestions").json()
    assert len([s for s in pending if s["match_value"] == "星巴克"]) == 1


def test_create_suggestion_invalid_category(client):
    resp = client.post("/api/v1/categories/rule-suggestions",
                       json={"match_value": "x", "category_l1": "不存在", "confidence": 0.8})
    assert resp.status_code == 400


# ── Approve / Reject ─────────────────────────────────────────────────────────

def test_approve_suggestion_creates_rule(client):
    sid = client.post("/api/v1/categories/rule-suggestions", json={
        "match_value": "肯德基", "category_l1": "餐饮",
        "category_l2": "快餐", "confidence": 0.95, "source": "llm_feedback",
    }).json()["id"]

    resp = client.post(f"/api/v1/categories/rule-suggestions/{sid}/approve")
    assert resp.status_code == 201
    assert resp.json()["match_value"] == "肯德基"

    # suggestion removed from pending
    assert not any(s["id"] == sid for s in
                   client.get("/api/v1/categories/rule-suggestions").json())
    # rule is now listed
    assert any(r["match_value"] == "肯德基" for r in
               client.get("/api/v1/categories/rules").json())


def test_approve_twice_returns_400(client):
    sid = client.post("/api/v1/categories/rule-suggestions", json={
        "match_value": "麦当劳", "category_l1": "餐饮",
        "category_l2": "快餐", "confidence": 0.9, "source": "llm_feedback",
    }).json()["id"]
    client.post(f"/api/v1/categories/rule-suggestions/{sid}/approve")
    resp = client.post(f"/api/v1/categories/rule-suggestions/{sid}/approve")
    assert resp.status_code == 400


def test_reject_suggestion(client):
    sid = client.post("/api/v1/categories/rule-suggestions", json={
        "match_value": "某某商家", "category_l1": "购物",
        "category_l2": "日用品", "confidence": 0.7, "source": "llm_feedback",
    }).json()["id"]

    resp = client.post(f"/api/v1/categories/rule-suggestions/{sid}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    rejected = client.get("/api/v1/categories/rule-suggestions?status=rejected").json()
    assert any(s["id"] == sid for s in rejected)
    assert not any(s["id"] == sid for s in
                   client.get("/api/v1/categories/rule-suggestions").json())


def test_reject_nonexistent_returns_404(client):
    assert client.post("/api/v1/categories/rule-suggestions/bad-id/reject").status_code == 404


# ── Generate suggestions from history ────────────────────────────────────────

def test_generate_no_history(client):
    resp = client.post("/api/v1/categories/rule-suggestions/generate")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_generate_from_high_confidence_llm(client):
    _seed_transaction(merchant="海底捞", category_l1="餐饮", category_l2="正餐",
                      category_source="llm", confidence=0.92)
    _seed_transaction(merchant="海底捞", category_l1="餐饮", category_l2="正餐",
                      category_source="llm", confidence=0.88)

    resp = client.post("/api/v1/categories/rule-suggestions/generate")
    assert resp.status_code == 200
    merchants = [item["match_value"] for item in resp.json()["items"]]
    assert "海底捞" in merchants


def test_generate_skips_low_confidence(client):
    _seed_transaction(merchant="不知名商家", category_l1="餐饮", category_l2="其他",
                      category_source="llm", confidence=0.6)

    resp = client.post("/api/v1/categories/rule-suggestions/generate")
    merchants = [item["match_value"] for item in resp.json()["items"]]
    assert "不知名商家" not in merchants


def test_generate_manual_override_always_included(client):
    """One manual correction → suggestion regardless of count."""
    _seed_transaction(merchant="某精品咖啡", category_l1="餐饮", category_l2="咖啡",
                      category_source="manual", confidence=1.0)

    resp = client.post("/api/v1/categories/rule-suggestions/generate")
    merchants = [item["match_value"] for item in resp.json()["items"]]
    assert "某精品咖啡" in merchants


def test_generate_skips_existing_rule(client):
    client.post("/api/v1/categories/rules", json={
        "match_value": "已有规则商家", "category_l1": "餐饮",
        "category_l2": "堂食", "priority": 10,
    })
    _seed_transaction(merchant="已有规则商家", category_l1="餐饮", category_l2="堂食",
                      category_source="manual", confidence=1.0)

    resp = client.post("/api/v1/categories/rule-suggestions/generate")
    merchants = [item["match_value"] for item in resp.json()["items"]]
    assert "已有规则商家" not in merchants


# ── Manual category update creates suggestion ─────────────────────────────────

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

    tx_id = _seed_transaction(merchant="某烤肉店", category_l1="其他",
                              category_source="fallback", confidence=0.0)

    resp = client.patch(f"/api/v1/transactions/{tx_id}/category",
                        json={"category_l1": "餐饮", "category_l2": "堂食"})
    assert resp.status_code == 200

    pending = client.get("/api/v1/categories/rule-suggestions").json()
    matching = [s for s in pending if s["match_value"] == "某烤肉店"]
    assert len(matching) == 1
    assert matching[0]["category_l1"] == "餐饮"
    assert matching[0]["source"] == "manual_feedback"


def test_manual_update_no_suggestion_for_empty_merchant(client, monkeypatch):
    import app.infrastructure.persistence.repositories.transaction_repo as _repo
    import app.domain.beancount.engine as _engine

    monkeypatch.setattr(_repo, "save_beancount_entry", lambda *a, **kw: None)

    class _FakeEntry:
        date = "2026-01-15"
        postings = []
        def render(self): return ""

    monkeypatch.setattr(_engine.BeancountEngine, "generate_entry",
                        lambda self, tx: _FakeEntry())

    tx_id = _seed_transaction(merchant="", category_l1="其他",
                              category_source="fallback", confidence=0.0)

    resp = client.patch(f"/api/v1/transactions/{tx_id}/category",
                        json={"category_l1": "餐饮", "category_l2": "外卖"})
    assert resp.status_code == 200
    assert client.get("/api/v1/categories/rule-suggestions").json() == []
