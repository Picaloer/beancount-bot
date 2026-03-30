from datetime import datetime
from uuid import uuid4

from app.domain.transaction.models import BillSource, RawTransaction, TransactionDirection, build_transaction_dedupe_key
from app.infrastructure.parsers.alipay import AlipayParser
from app.infrastructure.persistence.database import Base, SessionLocal, engine
from app.infrastructure.persistence.models.orm_models import BillImportORM, TransactionORM
from app.infrastructure.persistence.repositories.transaction_repo import bulk_create_transactions, ensure_user

import app.infrastructure.persistence.models.orm_models  # noqa: F401


Base.metadata.create_all(bind=engine)
USER_ID = "00000000-0000-0000-0000-000000000001"


def _create_import(source: str = "wechat") -> str:
    db = SessionLocal()
    try:
        ensure_user(db, USER_ID)
        import_id = str(uuid4())
        db.add(
            BillImportORM(
                id=import_id,
                user_id=USER_ID,
                source=source,
                file_name=f"{source}.csv",
                status="done",
            )
        )
        db.commit()
        return import_id
    finally:
        db.close()


def _cleanup_tables() -> None:
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


def test_bulk_create_transactions_dedupes_cross_source_by_fingerprint():
    _cleanup_tables()
    wechat_import_id = _create_import("wechat")
    cmb_import_id = _create_import("cmb")

    tx_time = datetime(2026, 3, 20, 12, 30)
    fingerprint = build_transaction_dedupe_key(
        direction=TransactionDirection.EXPENSE,
        amount=88.0,
        currency="CNY",
        merchant="瑞幸咖啡",
        description="生椰拿铁",
        transaction_at=tx_time,
    )

    db = SessionLocal()
    try:
        inserted_first = bulk_create_transactions(
            db,
            wechat_import_id,
            USER_ID,
            [
                RawTransaction(
                    source=BillSource.WECHAT,
                    direction=TransactionDirection.EXPENSE,
                    amount=88.0,
                    currency="CNY",
                    merchant="瑞幸咖啡",
                    description="生椰拿铁",
                    transaction_at=tx_time,
                    raw_data={"交易单号": "wx-1"},
                    external_id="merchant-order-1",
                    dedupe_key=fingerprint,
                )
            ],
        )
        inserted_second = bulk_create_transactions(
            db,
            cmb_import_id,
            USER_ID,
            [
                RawTransaction(
                    source=BillSource.CMB,
                    direction=TransactionDirection.EXPENSE,
                    amount=88.0,
                    currency="CNY",
                    merchant="瑞幸咖啡",
                    description="生椰拿铁",
                    transaction_at=tx_time,
                    raw_data={"交易摘要": "生椰拿铁"},
                    external_id="cmb:row-1",
                    dedupe_key=fingerprint,
                )
            ],
        )

        assert len(inserted_first) == 1
        assert inserted_second == []
        assert db.query(TransactionORM).count() == 1
    finally:
        db.close()


def test_bulk_create_transactions_dedupes_shared_external_id_across_sources():
    _cleanup_tables()
    wechat_import_id = _create_import("wechat")
    alipay_import_id = _create_import("alipay")

    db = SessionLocal()
    try:
        inserted_first = bulk_create_transactions(
            db,
            wechat_import_id,
            USER_ID,
            [
                RawTransaction(
                    source=BillSource.WECHAT,
                    direction=TransactionDirection.EXPENSE,
                    amount=120.0,
                    currency="CNY",
                    merchant="盒马",
                    description="订单支付",
                    transaction_at=datetime(2026, 3, 21, 9, 15),
                    raw_data={"商户单号": "shared-order-1"},
                    external_id="shared-order-1",
                    dedupe_key="wechat-key",
                )
            ],
        )
        inserted_second = bulk_create_transactions(
            db,
            alipay_import_id,
            USER_ID,
            [
                RawTransaction(
                    source=BillSource.ALIPAY,
                    direction=TransactionDirection.EXPENSE,
                    amount=120.0,
                    currency="CNY",
                    merchant="盒马",
                    description="订单支付",
                    transaction_at=datetime(2026, 3, 21, 9, 15),
                    raw_data={"商家订单号": "shared-order-1"},
                    external_id="shared-order-1",
                    dedupe_key="alipay-key",
                )
            ],
        )

        assert len(inserted_first) == 1
        assert inserted_second == []
        assert db.query(TransactionORM).count() == 1
    finally:
        db.close()


def test_alipay_parser_prefers_merchant_order_id_for_duplicate_variants():
    parser = AlipayParser()

    first = parser._parse_row(
        {
            "交易时间": "2026-03-28 22:00:20",
            "交易分类": "商业服务",
            "交易对方": "深空补给站72751",
            "商品说明": "轨道舱服务订购72751",
            "收/支": "支出",
            "金额": "49.81",
            "交易状态": "交易成功",
            "交易订单号": "LLM177485727501",
            "商家订单号": "30P2088431103081731W03_100426032822000998845302",
        }
    )
    second = parser._parse_row(
        {
            "交易时间": "2026-03-28 23:00:14",
            "交易分类": "商业服务",
            "交易对方": "杭州深度求索",
            "商品说明": "DeepSeekAPI服务",
            "收/支": "支出",
            "金额": "49.81",
            "交易状态": "交易成功",
            "交易订单号": "2026032823001465511424074173",
            "商家订单号": "30P2088431103081731W03_100426032822000998845302",
        }
    )

    assert first is not None
    assert second is not None
    assert first.external_id == "30P2088431103081731W03_100426032822000998845302"
    assert second.external_id == "30P2088431103081731W03_100426032822000998845302"


def test_bulk_create_transactions_dedupes_alipay_variants_with_same_merchant_order_id():
    _cleanup_tables()
    import_id = _create_import("alipay")
    parser = AlipayParser()

    first = parser._parse_row(
        {
            "交易时间": "2026-03-28 22:00:20",
            "交易分类": "商业服务",
            "交易对方": "深空补给站72751",
            "商品说明": "轨道舱服务订购72751",
            "收/支": "支出",
            "金额": "49.81",
            "交易状态": "交易成功",
            "交易订单号": "LLM177485727501",
            "商家订单号": "30P2088431103081731W03_100426032822000998845302",
        }
    )
    second = parser._parse_row(
        {
            "交易时间": "2026-03-28 23:00:14",
            "交易分类": "商业服务",
            "交易对方": "杭州深度求索",
            "商品说明": "DeepSeekAPI服务",
            "收/支": "支出",
            "金额": "49.81",
            "交易状态": "交易成功",
            "交易订单号": "2026032823001465511424074173",
            "商家订单号": "30P2088431103081731W03_100426032822000998845302",
        }
    )

    assert first is not None
    assert second is not None

    db = SessionLocal()
    try:
        inserted = bulk_create_transactions(db, import_id, USER_ID, [first, second])

        assert len(inserted) == 1
        assert inserted[0][0].external_id == "30P2088431103081731W03_100426032822000998845302"
        assert db.query(TransactionORM).count() == 1
    finally:
        db.close()
