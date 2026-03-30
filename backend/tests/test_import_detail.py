from datetime import timedelta
from uuid import uuid4

from app.core.timezone import now_beijing
from app.infrastructure.persistence.database import Base, SessionLocal, engine
from app.infrastructure.persistence.models.orm_models import BillImportORM
from app.infrastructure.persistence.repositories.transaction_repo import (
    create_import,
    ensure_user,
    get_import_detail,
    update_import_stage,
    update_import_status,
    update_import_summary,
)

import app.infrastructure.persistence.models.orm_models  # noqa: F401


Base.metadata.create_all(bind=engine)
USER_ID = "00000000-0000-0000-0000-000000000001"


def _cleanup_tables() -> None:
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


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
            "classify",
            "beancount",
        ]
        assert all(stage["status"] == "pending" for stage in detail["stages"])
        assert detail["summary"] == {
            "inserted_count": 0,
            "duplicate_count": 0,
            "beancount_entry_count": 0,
            "rule_based_count": 0,
            "llm_based_count": 0,
            "fallback_count": 0,
            "low_confidence_count": 0,
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
        classify_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "classify")
        beancount_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "beancount")
        assert classify_stage["finished_at"] == expected_finished_at
        assert beancount_stage["finished_at"] == expected_finished_at
        assert detail["finished_at"] >= beancount_stage["finished_at"]
    finally:
        db.close()
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
        assert detail["summary"]["llm_based_count"] == 6
        classify_stage = next(stage for stage in detail["stages"] if stage["stage_key"] == "classify")
        assert classify_stage["status"] == "processing"
        assert classify_stage["message"] == "正在分类交易"
    finally:
        db.close()
