from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.timezone import now_beijing
from app.infrastructure.persistence.database import Base, SessionLocal, engine, get_db
from app.infrastructure.persistence.models.orm_models import BillImportORM, DuplicateReviewGroupORM, TransactionORM
from app.infrastructure.persistence.repositories.transaction_repo import (
    create_import,
    ensure_user,
    get_import_detail,
    update_import_stage,
    update_import_status,
    update_import_summary,
)

import app.infrastructure.persistence.models.orm_models  # noqa: F401
from app.main import app as fastapi_app


Base.metadata.create_all(bind=engine)
USER_ID = "00000000-0000-0000-0000-000000000001"


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = override_get_db


def _cleanup_tables() -> None:
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


def _seed_duplicate_review_group() -> tuple[str, str, str, str]:
    db = SessionLocal()
    try:
        ensure_user(db, USER_ID)
        imp = create_import(db, USER_ID, "wechat", "wechat.csv")
        update_import_status(
            db,
            imp.id,
            status="reviewing_duplicates",
            row_count=2,
            total_rows=2,
            processed_rows=0,
            llm_total_batches=0,
            llm_completed_batches=0,
            stage_message="发现 1 组疑似重复交易，等待确认",
        )
        update_import_stage(
            db,
            imp.id,
            "parse",
            status="done",
            message="已解析 2 条原始交易",
            finished_at=now_beijing(),
        )
        update_import_stage(
            db,
            imp.id,
            "dedupe",
            status="done",
            message="新增 2 条，识别重复 0 条",
            finished_at=now_beijing(),
        )
        update_import_stage(
            db,
            imp.id,
            "duplicate_review",
            status="processing",
            message="发现 1 组跨来源疑似重复交易，等待人工确认",
            started_at=now_beijing(),
        )
        update_import_summary(
            db,
            imp.id,
            inserted_count=2,
            duplicate_count=0,
            duplicate_review_group_count=1,
            duplicate_review_pair_count=1,
            duplicate_review_resolved_count=0,
        )

        group_id = str(uuid4())
        group = DuplicateReviewGroupORM(
            id=group_id,
            import_id=imp.id,
            user_id=USER_ID,
            review_status="pending",
            review_reason="跨账单来源且同日同金额，需人工确认是否为同一笔交易。",
            ai_suggestion="needs_review",
            ai_reason="当前仅按跨来源同日同金额进行初筛，待接入 AI 细化判断。",
            candidate_date="2026-01-15",
            candidate_amount=38.5,
            candidate_currency="CNY",
            transaction_count=2,
        )
        db.add(group)

        tx_keep_id = str(uuid4())
        tx_remove_id = str(uuid4())
        db.add(
            TransactionORM(
                id=tx_keep_id,
                user_id=USER_ID,
                import_id=imp.id,
                source="wechat",
                direction="expense",
                amount=38.5,
                currency="CNY",
                merchant="美团外卖",
                description="午餐",
                transaction_at=now_beijing(),
                duplicate_review_status="pending",
                duplicate_review_group_id=group_id,
            )
        )
        db.add(
            TransactionORM(
                id=tx_remove_id,
                user_id=USER_ID,
                import_id=imp.id,
                source="alipay",
                direction="expense",
                amount=38.5,
                currency="CNY",
                merchant="美团外卖",
                description="午餐",
                transaction_at=now_beijing(),
                duplicate_review_status="pending",
                duplicate_review_group_id=group_id,
            )
        )
        db.commit()
        return imp.id, group_id, tx_keep_id, tx_remove_id
    finally:
        db.close()


def test_create_import_initializes_stages_and_summary():
    _cleanup_tables()
    db = SessionLocal()
    try:
        imp = create_import(db, USER_ID, "wechat", "wechat.csv")

        detail = get_import_detail(db, imp.id, USER_ID)

        assert detail is not None
        assert detail["import_id"] == imp.id
        assert [stage["stage_key"] for stage in detail["stages"]] == [
            "parse",
            "dedupe",
            "duplicate_review",
            "classify",
            "beancount",
        ]
        assert all(stage["status"] == "pending" for stage in detail["stages"])
        assert detail["summary"] == {
            "inserted_count": 0,
            "duplicate_count": 0,
            "duplicate_review_group_count": 0,
            "duplicate_review_pair_count": 0,
            "duplicate_review_resolved_count": 0,
            "beancount_entry_count": 0,
            "rule_based_count": 0,
            "llm_based_count": 0,
            "fallback_count": 0,
            "low_confidence_count": 0,
        }
        assert detail["duplicate_review"] == {
            "group_count": 0,
            "pending_count": 0,
            "resolved_count": 0,
            "groups": [],
        }
    finally:
        db.close()


def test_import_detail_preserves_monotonic_stage_timestamps():
    _cleanup_tables()
    db = SessionLocal()
    try:
        imp = create_import(db, USER_ID, "alipay", "alipay.csv")
        started_at = now_beijing()
        finished_at = started_at + timedelta(seconds=5)

        update_import_stage(
            db,
            imp.id,
            "beancount",
            status="processing",
            message="正在生成 Beancount 分录",
            started_at=started_at,
        )
        update_import_stage(
            db,
            imp.id,
            "beancount",
            status="done",
            message="已生成 3 条 Beancount 分录",
            finished_at=finished_at,
        )
        update_import_status(
            db,
            imp.id,
            status="done",
            stage_message="导入完成",
            finished_at=finished_at,
        )

        detail = get_import_detail(db, imp.id, USER_ID)

        assert detail is not None
        assert detail["finished_at"] == detail["stages"][-1]["finished_at"]
        beancount_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "beancount")
        assert beancount_stage["started_at"] is not None
        assert beancount_stage["finished_at"] is not None
        assert beancount_stage["started_at"] < beancount_stage["finished_at"]
        assert detail["finished_at"] >= beancount_stage["finished_at"]
    finally:
        db.close()


def test_import_detail_preserves_duplicate_only_completion_timestamps():
    _cleanup_tables()
    db = SessionLocal()
    try:
        imp = create_import(db, USER_ID, "alipay", "alipay.csv")
        finished_at = now_beijing()

        update_import_stage(
            db,
            imp.id,
            "dedupe",
            status="done",
            message="新增 0 条，识别重复 10 条",
            finished_at=finished_at,
        )
        update_import_stage(
            db,
            imp.id,
            "duplicate_review",
            status="done",
            message="无需复核，全部为重复交易",
            finished_at=finished_at,
        )
        update_import_stage(
            db,
            imp.id,
            "classify",
            status="done",
            message="无需分类，全部为重复交易",
            finished_at=finished_at,
        )
        update_import_stage(
            db,
            imp.id,
            "beancount",
            status="done",
            message="无需生成分录，全部为重复交易",
            finished_at=finished_at,
        )
        update_import_status(
            db,
            imp.id,
            status="done",
            row_count=0,
            processed_rows=0,
            llm_total_batches=0,
            llm_completed_batches=0,
            stage_message="导入完成，全部为重复交易",
            finished_at=finished_at,
        )

        expected_finished_at = finished_at.isoformat() + "+08:00"

        detail = get_import_detail(db, imp.id, USER_ID)

        assert detail is not None
        assert detail["finished_at"] == expected_finished_at
        duplicate_review_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "duplicate_review")
        classify_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "classify")
        beancount_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "beancount")
        assert duplicate_review_stage["finished_at"] == expected_finished_at
        assert classify_stage["finished_at"] == expected_finished_at
        assert beancount_stage["finished_at"] == expected_finished_at
        assert detail["finished_at"] >= beancount_stage["finished_at"]
    finally:
        db.close()


def test_import_detail_includes_progress_metrics():
    _cleanup_tables()
    db = SessionLocal()
    try:
        ensure_user(db, USER_ID)
        import_id = str(uuid4())
        db.add(
            BillImportORM(
                id=import_id,
                user_id=USER_ID,
                source="wechat",
                file_name="wechat.csv",
                status="processing",
            )
        )
        db.commit()

        create_import(db, USER_ID, "alipay", "alipay.csv")
        target = db.query(BillImportORM).filter(BillImportORM.id != import_id).first()
        assert target is not None

        update_import_status(
            db,
            target.id,
            status="classifying",
            row_count=12,
            total_rows=15,
            processed_rows=8,
            llm_total_batches=2,
            llm_completed_batches=1,
            input_tokens=100,
            output_tokens=40,
            stage_message="正在进行 AI 分类",
        )
        update_import_stage(
            db,
            target.id,
            "parse",
            status="done",
            message="已解析 15 条原始交易",
        )
        update_import_stage(
            db,
            target.id,
            "classify",
            status="processing",
            message="正在分类交易",
        )
        update_import_summary(
            db,
            target.id,
            inserted_count=12,
            duplicate_count=3,
            duplicate_review_group_count=2,
            duplicate_review_pair_count=2,
            duplicate_review_resolved_count=1,
            beancount_entry_count=10,
            rule_based_count=5,
            llm_based_count=6,
            fallback_count=1,
            low_confidence_count=2,
        )

        detail = get_import_detail(db, target.id, USER_ID)

        assert detail is not None
        assert detail["status"] == "classifying"
        assert detail["row_count"] == 12
        assert detail["total_rows"] == 15
        assert detail["processed_rows"] == 8
        assert detail["total_tokens"] == 140
        assert detail["summary"]["duplicate_count"] == 3
        assert detail["summary"]["duplicate_review_group_count"] == 2
        assert detail["summary"]["duplicate_review_resolved_count"] == 1
        assert detail["summary"]["llm_based_count"] == 6
        classify_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "classify")
        assert classify_stage["status"] == "processing"
        assert classify_stage["message"] == "正在分类交易"
    finally:
        db.close()


def test_delete_import_endpoint_returns_404_for_missing_import():
    _cleanup_tables()

    with TestClient(fastapi_app, raise_server_exceptions=True) as client:
        response = client.delete(
            "/api/v1/bills/import/00000000-0000-0000-0000-000000000099",
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Import 00000000-0000-0000-0000-000000000099 not found"}


def test_delete_import_endpoint_deletes_reviewing_duplicates_import():
    _cleanup_tables()
    import_id, _group_id, _tx_keep_id, _tx_remove_id = _seed_duplicate_review_group()

    with TestClient(fastapi_app, raise_server_exceptions=True) as client:
        response = client.delete(f"/api/v1/bills/import/{import_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["import_id"] == import_id
    assert payload["deleted_transactions"] == 2

    db = SessionLocal()
    try:
        assert get_import_detail(db, import_id, USER_ID) is None
    finally:
        db.close()


def test_delete_import_endpoint_rejects_processing_import():
    _cleanup_tables()
    db = SessionLocal()
    try:
        imp = create_import(db, USER_ID, "wechat", "wechat.csv")
        import_id = imp.id
        update_import_status(
            db,
            import_id,
            status="processing",
            stage_message="正在解析账单",
        )
    finally:
        db.close()

    with TestClient(fastapi_app, raise_server_exceptions=True) as client:
        response = client.delete(f"/api/v1/bills/import/{import_id}")

    assert response.status_code == 409
    assert response.json() == {"detail": "Cannot delete an import that is currently being processed"}
    _cleanup_tables()
    import_id, group_id, tx_keep_id, tx_remove_id = _seed_duplicate_review_group()

    with TestClient(fastapi_app, raise_server_exceptions=True) as client:
        response = client.post(
            f"/api/v1/bills/import/{import_id}/duplicate-review/{group_id}/resolve",
            json={"kept_transaction_id": tx_keep_id, "review_reason": "保留微信账单记录"},
        )

    assert response.status_code == 200
    assert response.json() == {"group_id": group_id, "review_status": "resolved"}

    db = SessionLocal()
    try:
        detail = get_import_detail(db, import_id, USER_ID)
        assert detail is not None
        assert detail["status"] == "done"
        assert detail["duplicate_review"]["pending_count"] == 0
        assert detail["duplicate_review"]["resolved_count"] == 1
        assert detail["summary"]["duplicate_review_resolved_count"] == 1
        assert detail["summary"]["inserted_count"] == 1
        assert detail["row_count"] == 1

        group = next(group for group in detail["duplicate_review"]["groups"] if group["group_id"] == group_id)
        assert group["review_status"] == "resolved"
        assert group["review_reason"] == "保留微信账单记录"

        statuses = {tx["transaction_id"]: tx["duplicate_review_status"] for tx in group["transactions"]}
        assert statuses[tx_keep_id] == "kept"
        assert statuses[tx_remove_id] == "removed"

        classify_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "classify")
        beancount_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "beancount")
        assert classify_stage["status"] == "done"
        assert beancount_stage["status"] == "done"
    finally:
        db.close()


def test_resolve_duplicate_review_group_endpoint_returns_404_for_missing_group():
    _cleanup_tables()
    import_id, _group_id, tx_keep_id, _tx_remove_id = _seed_duplicate_review_group()
    missing_group_id = str(uuid4())

    with TestClient(fastapi_app, raise_server_exceptions=True) as client:
        response = client.post(
            f"/api/v1/bills/import/{import_id}/duplicate-review/{missing_group_id}/resolve",
            json={"kept_transaction_id": tx_keep_id},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Duplicate review group not found"}


def test_resolve_duplicate_review_group_endpoint_returns_400_when_import_not_waiting_review():
    _cleanup_tables()
    import_id, group_id, tx_keep_id, _tx_remove_id = _seed_duplicate_review_group()

    db = SessionLocal()
    try:
        update_import_status(
            db,
            import_id,
            status="classifying",
            stage_message="正在进行 AI 分类",
        )
    finally:
        db.close()

    with TestClient(fastapi_app, raise_server_exceptions=True) as client:
        response = client.post(
            f"/api/v1/bills/import/{import_id}/duplicate-review/{group_id}/resolve",
            json={"kept_transaction_id": tx_keep_id},
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Import is not waiting for duplicate review"}


def test_resolve_duplicate_review_group_endpoint_keeps_import_waiting_when_other_groups_pending():
    _cleanup_tables()
    first_import_id, first_group_id, first_keep_id, first_remove_id = _seed_duplicate_review_group()

    db = SessionLocal()
    try:
        second_group_id = str(uuid4())
        second_keep_id = str(uuid4())
        second_remove_id = str(uuid4())
        group = DuplicateReviewGroupORM(
            id=second_group_id,
            import_id=first_import_id,
            user_id=USER_ID,
            review_status="pending",
            review_reason="跨账单来源且同日同金额，需人工确认是否为同一笔交易。",
            ai_suggestion="needs_review",
            ai_reason="当前仅按跨来源同日同金额进行初筛，待接入 AI 细化判断。",
            candidate_date="2026-01-16",
            candidate_amount=52.0,
            candidate_currency="CNY",
            transaction_count=2,
        )
        db.add(group)
        db.add(
            TransactionORM(
                id=second_keep_id,
                user_id=USER_ID,
                import_id=first_import_id,
                source="wechat",
                direction="expense",
                amount=52.0,
                currency="CNY",
                merchant="盒马鲜生",
                description="买菜",
                transaction_at=now_beijing(),
                duplicate_review_status="pending",
                duplicate_review_group_id=second_group_id,
            )
        )
        db.add(
            TransactionORM(
                id=second_remove_id,
                user_id=USER_ID,
                import_id=first_import_id,
                source="alipay",
                direction="expense",
                amount=52.0,
                currency="CNY",
                merchant="盒马鲜生",
                description="买菜",
                transaction_at=now_beijing(),
                duplicate_review_status="pending",
                duplicate_review_group_id=second_group_id,
            )
        )
        update_import_summary(
            db,
            first_import_id,
            inserted_count=4,
            duplicate_count=0,
            duplicate_review_group_count=2,
            duplicate_review_pair_count=2,
            duplicate_review_resolved_count=0,
        )
        db.commit()
    finally:
        db.close()

    with TestClient(fastapi_app, raise_server_exceptions=True) as client:
        response = client.post(
            f"/api/v1/bills/import/{first_import_id}/duplicate-review/{first_group_id}/resolve",
            json={"kept_transaction_id": first_keep_id, "review_reason": "先保留微信午餐记录"},
        )

    assert response.status_code == 200
    assert response.json() == {"group_id": first_group_id, "review_status": "resolved"}

    db = SessionLocal()
    try:
        detail = get_import_detail(db, first_import_id, USER_ID)
        assert detail is not None
        assert detail["status"] == "reviewing_duplicates"
        assert detail["stage_message"] == "仍有 1 组疑似重复交易待确认"
        assert detail["duplicate_review"]["pending_count"] == 1
        assert detail["duplicate_review"]["resolved_count"] == 1
        assert detail["summary"]["duplicate_review_group_count"] == 2
        assert detail["summary"]["duplicate_review_resolved_count"] == 1
        assert detail["summary"]["inserted_count"] == 4

        groups = {group["group_id"]: group for group in detail["duplicate_review"]["groups"]}
        first_group = groups[first_group_id]
        second_group = groups[second_group_id]
        assert first_group["review_status"] == "resolved"
        assert second_group["review_status"] == "pending"

        first_statuses = {tx["transaction_id"]: tx["duplicate_review_status"] for tx in first_group["transactions"]}
        second_statuses = {tx["transaction_id"]: tx["duplicate_review_status"] for tx in second_group["transactions"]}
        assert first_statuses[first_keep_id] == "kept"
        assert first_statuses[first_remove_id] == "removed"
        assert second_statuses[second_keep_id] == "pending"
        assert second_statuses[second_remove_id] == "pending"

        classify_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "classify")
        beancount_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "beancount")
        assert classify_stage["status"] == "pending"
        assert beancount_stage["status"] == "pending"
    finally:
        db.close()


