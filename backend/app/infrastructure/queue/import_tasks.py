"""
Celery task: process a bill import end-to-end.
  1. Parse file → RawTransactions
  2. Bulk insert to DB
  3. Run classification pipeline
  4. Generate Beancount entries
  5. Update import status
"""
import logging
from dataclasses import dataclass

from sqlalchemy import func, select

from app.core.timezone import now_beijing
from app.domain.classification.batch_runner import BatchProgressUpdate, classify_transactions
from app.infrastructure.queue.celery_app import celery_app

logger = logging.getLogger(__name__)


@dataclass
class ClassificationContinuationResult:
    kept_count: int
    removed_count: int
    processed_rows: int
    llm_total_batches: int
    llm_completed_batches: int
    input_tokens: int
    output_tokens: int
    rule_based_count: int
    llm_based_count: int
    fallback_count: int
    low_confidence_count: int
    beancount_entry_count: int


@celery_app.task(name="import_tasks.process_bill_import", bind=True, max_retries=3)
def process_bill_import(self, import_id: str, file_path: str, user_id: str) -> dict:
    """Main import pipeline task."""
    from app.domain.beancount.engine import BeancountEngine
    from app.domain.transaction.models import Transaction
    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.repositories import transaction_repo as repo
    from app.infrastructure.parsers import registry as parser_registry

    db = SessionLocal()
    try:
        repo.update_import_status(
            db,
            import_id,
            status="processing",
            stage_message="正在解析账单",
            started_at=now_beijing(),
            finished_at=None,
            processed_rows=0,
            llm_completed_batches=0,
            input_tokens=0,
            output_tokens=0,
        )
        repo.update_import_stage(
            db,
            import_id,
            "parse",
            status="processing",
            message="正在解析账单",
            started_at=now_beijing(),
        )

        source_type, raw_transactions = parser_registry.parse_file(file_path)
        logger.info("Parsed %d transactions from %s", len(raw_transactions), source_type)
        repo.update_import_stage(
            db,
            import_id,
            "parse",
            status="done",
            message=f"已解析 {len(raw_transactions)} 条原始交易",
            finished_at=now_beijing(),
        )

        if not raw_transactions:
            finished_at = now_beijing()
            repo.update_import_status(
                db,
                import_id,
                status="done",
                row_count=0,
                total_rows=0,
                processed_rows=0,
                llm_total_batches=0,
                llm_completed_batches=0,
                stage_message="账单为空",
                finished_at=finished_at,
            )
            repo.update_import_stage(
                db,
                import_id,
                "dedupe",
                status="done",
                message="无需去重，没有可导入交易",
                finished_at=finished_at,
            )
            repo.update_import_stage(
                db,
                import_id,
                "duplicate_review",
                status="done",
                message="无需复核，没有可导入交易",
                finished_at=finished_at,
            )
            repo.update_import_stage(
                db,
                import_id,
                "classify",
                status="done",
                message="无需分类，没有可导入交易",
                finished_at=finished_at,
            )
            repo.update_import_stage(
                db,
                import_id,
                "beancount",
                status="done",
                message="无需生成分录，没有可导入交易",
                finished_at=finished_at,
            )
            repo.update_import_summary(
                db,
                import_id,
                inserted_count=0,
                duplicate_count=0,
                beancount_entry_count=0,
                rule_based_count=0,
                llm_based_count=0,
                fallback_count=0,
                low_confidence_count=0,
            )
            return {"import_id": import_id, "count": 0}

        repo.update_import_status(
            db,
            import_id,
            total_rows=len(raw_transactions),
            stage_message="正在写入交易记录",
        )
        repo.update_import_stage(
            db,
            import_id,
            "dedupe",
            status="processing",
            message="正在识别重复交易并写入新交易",
            started_at=now_beijing(),
        )

        inserted_transactions = repo.bulk_create_transactions(db, import_id, user_id, raw_transactions)
        duplicate_count = len(raw_transactions) - len(inserted_transactions)
        repo.update_import_stage(
            db,
            import_id,
            "dedupe",
            status="done",
            message=f"新增 {len(inserted_transactions)} 条，识别重复 {duplicate_count} 条",
            finished_at=now_beijing(),
        )
        repo.update_import_summary(
            db,
            import_id,
            inserted_count=len(inserted_transactions),
            duplicate_count=duplicate_count,
        )

        duplicate_review_groups = repo.create_duplicate_review_groups(db, import_id, user_id)
        if duplicate_review_groups:
            waiting_started_at = now_beijing()
            repo.update_import_stage(
                db,
                import_id,
                "duplicate_review",
                status="processing",
                message=f"发现 {len(duplicate_review_groups)} 组跨来源疑似重复交易，等待人工确认",
                started_at=waiting_started_at,
            )
            repo.update_import_status(
                db,
                import_id,
                status="reviewing_duplicates",
                row_count=len(inserted_transactions),
                processed_rows=0,
                llm_total_batches=0,
                llm_completed_batches=0,
                stage_message=f"发现 {len(duplicate_review_groups)} 组疑似重复交易，等待确认",
            )
            logger.info("Import %s paused for duplicate review: %d groups", import_id, len(duplicate_review_groups))
            return {
                "import_id": import_id,
                "count": len(inserted_transactions),
                "status": "reviewing_duplicates",
                "duplicate_review_groups": len(duplicate_review_groups),
            }

        continuation = _continue_import_after_duplicate_review(db, import_id, user_id)
        logger.info("Import %s complete: %d transactions", import_id, continuation.processed_rows)
        return {"import_id": import_id, "count": continuation.processed_rows}

    except Exception as exc:
        logger.exception("Import task failed for %s", import_id)
        repo.update_import_status(
            db,
            import_id,
            status="failed",
            stage_message="导入失败",
            error=str(exc),
            finished_at=now_beijing(),
        )
        for stage_key in ("parse", "dedupe", "duplicate_review", "classify", "beancount"):
            repo.update_import_stage(
                db,
                import_id,
                stage_key,
                status="failed",
                message="导入失败",
                finished_at=now_beijing(),
            )
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


def resume_import_after_duplicate_review(import_id: str, user_id: str) -> dict:
    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.repositories import transaction_repo as repo

    db = SessionLocal()
    try:
        if repo.has_pending_duplicate_reviews(db, import_id):
            raise ValueError("Duplicate review is not complete")

        continuation = _continue_import_after_duplicate_review(db, import_id, user_id)
        return {
            "import_id": import_id,
            "status": "done",
            "count": continuation.processed_rows,
            "kept_count": continuation.kept_count,
            "removed_count": continuation.removed_count,
        }
    finally:
        db.close()


def _continue_import_after_duplicate_review(db, import_id: str, user_id: str) -> ClassificationContinuationResult:
    from app.domain.beancount.engine import BeancountEngine
    from app.domain.transaction.models import BillSource, CategorySource, RawTransaction, Transaction, TransactionDirection
    from app.infrastructure.persistence.models.orm_models import ImportStageORM, TransactionORM
    from app.infrastructure.persistence.repositories import transaction_repo as repo

    candidate_transactions = repo.list_import_transactions_for_classification(db, import_id, user_id)
    removed_count = db.scalar(
        select(func.count())
        .select_from(TransactionORM)
        .where(
            TransactionORM.import_id == import_id,
            TransactionORM.user_id == user_id,
            TransactionORM.duplicate_review_status == "removed",
        )
    ) or 0
    kept_count = len(candidate_transactions)

    duplicate_stage = db.scalar(
        select(ImportStageORM).where(
            ImportStageORM.import_id == import_id,
            ImportStageORM.stage_key == "duplicate_review",
        )
    )
    duplicate_started_at = duplicate_stage.started_at if duplicate_stage and duplicate_stage.started_at else now_beijing()
    duplicate_message = (
        f"已完成 {len(candidate_transactions) + removed_count} 条候选交易复核，保留 {kept_count} 条，移除 {removed_count} 条"
        if removed_count > 0
        else "未发现需要人工复核的跨来源疑似重复交易"
    )
    repo.update_import_stage(
        db,
        import_id,
        "duplicate_review",
        status="done",
        message=duplicate_message,
        started_at=duplicate_started_at,
        finished_at=now_beijing(),
    )
    repo.mark_import_ready_for_classification(db, import_id)

    pipeline, agent, max_concurrency = _build_pipeline(db, user_id)
    llm_batch_size = agent.batch_size if agent else 0
    raw_transactions = [
        RawTransaction(
            source=BillSource(tx.source),
            direction=TransactionDirection(tx.direction),
            amount=float(tx.amount),
            currency=tx.currency,
            merchant=tx.merchant,
            description=tx.description,
            transaction_at=tx.transaction_at,
            raw_data=tx.raw_data or {},
            external_id=tx.external_id,
            dedupe_key=tx.dedupe_key,
        )
        for tx in candidate_transactions
    ]
    llm_candidate_count = (
        sum(1 for raw_tx in raw_transactions if pipeline.classify_before_llm(raw_tx) is None)
        if agent and llm_batch_size
        else 0
    )
    llm_total_batches = ((llm_candidate_count - 1) // llm_batch_size + 1) if llm_candidate_count else 0

    repo.update_import_status(
        db,
        import_id,
        status="classifying",
        row_count=kept_count,
        processed_rows=0,
        llm_total_batches=llm_total_batches,
        llm_completed_batches=0,
        input_tokens=0,
        output_tokens=0,
        stage_message="正在进行 AI 分类",
    )
    repo.update_import_stage(
        db,
        import_id,
        "classify",
        status="processing",
        message="正在分类交易",
        started_at=now_beijing(),
    )

    def on_progress(update: BatchProgressUpdate) -> None:
        repo.update_import_status(
            db,
            import_id,
            processed_rows=update.processed_rows,
            llm_completed_batches=update.llm_completed_batches,
            input_tokens=update.usage.input_tokens,
            output_tokens=update.usage.output_tokens,
            stage_message=_build_classification_stage_message(
                processed_rows=update.processed_rows,
                total_rows=kept_count,
                llm_completed_batches=update.llm_completed_batches,
                llm_total_batches=llm_total_batches,
            ),
        )

    batch_result = classify_transactions(
        raw_transactions,
        pipeline,
        agent,
        max_concurrency=max_concurrency,
        progress_callback=on_progress,
    )

    rule_based_count = sum(
        1 for result in batch_result.results if result.source.value in {"user_rule", "system_rule"}
    )
    llm_based_count = sum(1 for result in batch_result.results if result.source.value == "llm")
    fallback_count = sum(1 for result in batch_result.results if result.source.value == "fallback")
    low_confidence_count = sum(1 for result in batch_result.results if float(result.confidence) < 0.7)
    repo.update_import_stage(
        db,
        import_id,
        "classify",
        status="done",
        message=f"规则 {rule_based_count} 条，AI {llm_based_count} 条，兜底 {fallback_count} 条",
        finished_at=now_beijing(),
    )
    repo.update_import_summary(
        db,
        import_id,
        inserted_count=kept_count,
        rule_based_count=rule_based_count,
        llm_based_count=llm_based_count,
        fallback_count=fallback_count,
        low_confidence_count=low_confidence_count,
    )

    repo.update_import_status(
        db,
        import_id,
        processed_rows=batch_result.processed_rows,
        llm_total_batches=batch_result.llm_batches,
        llm_completed_batches=batch_result.llm_batches,
        input_tokens=batch_result.usage.input_tokens,
        output_tokens=batch_result.usage.output_tokens,
        stage_message="正在生成 Beancount 分录",
    )

    beancount_engine = BeancountEngine()
    beancount_entry_count = 0
    repo.update_import_stage(
        db,
        import_id,
        "beancount",
        status="processing",
        message="正在生成 Beancount 分录",
        started_at=now_beijing(),
    )

    for tx, result in zip(candidate_transactions, batch_result.results, strict=False):
        repo.update_transaction_category(
            db,
            tx.id,
            result.category_l1,
            result.category_l2,
            result.source.value,
            confidence=result.confidence,
        )
        domain_tx = Transaction(
            id=tx.id,
            user_id=user_id,
            import_id=import_id,
            source=BillSource(tx.source),
            direction=TransactionDirection(tx.direction),
            amount=float(tx.amount),
            currency=tx.currency,
            merchant=tx.merchant,
            description=tx.description,
            transaction_at=tx.transaction_at,
            category_l1=result.category_l1,
            category_l2=result.category_l2,
            category_source=CategorySource(result.source.value),
            raw_data=tx.raw_data or {},
        )
        try:
            entry = beancount_engine.generate_entry(domain_tx)
            postings = [
                {"account": p.account, "amount": str(p.amount), "currency": p.currency}
                for p in entry.postings
            ]
            repo.save_beancount_entry(db, tx.id, user_id, entry.date, entry.render(), postings)
            beancount_entry_count += 1
        except Exception as e:
            logger.warning("Beancount entry generation failed for %s: %s", tx.id, e)

    beancount_finished_at = now_beijing()
    repo.update_import_stage(
        db,
        import_id,
        "beancount",
        status="done",
        message=f"已生成 {beancount_entry_count} 条 Beancount 分录",
        finished_at=beancount_finished_at,
    )
    repo.update_import_status(
        db,
        import_id,
        status="done",
        row_count=kept_count,
        processed_rows=batch_result.processed_rows,
        llm_total_batches=batch_result.llm_batches,
        llm_completed_batches=batch_result.llm_batches,
        input_tokens=batch_result.usage.input_tokens,
        output_tokens=batch_result.usage.output_tokens,
        stage_message="导入完成",
        finished_at=beancount_finished_at,
    )
    repo.update_import_summary(
        db,
        import_id,
        inserted_count=kept_count,
        beancount_entry_count=beancount_entry_count,
        rule_based_count=rule_based_count,
        llm_based_count=llm_based_count,
        fallback_count=fallback_count,
        low_confidence_count=low_confidence_count,
    )

    return ClassificationContinuationResult(
        kept_count=kept_count,
        removed_count=removed_count,
        processed_rows=batch_result.processed_rows,
        llm_total_batches=batch_result.llm_batches,
        llm_completed_batches=batch_result.llm_batches,
        input_tokens=batch_result.usage.input_tokens,
        output_tokens=batch_result.usage.output_tokens,
        rule_based_count=rule_based_count,
        llm_based_count=llm_based_count,
        fallback_count=fallback_count,
        low_confidence_count=low_confidence_count,
        beancount_entry_count=beancount_entry_count,
    )


def _build_pipeline(db, user_id: str):
    """Build classification pipeline with user rules loaded from DB."""
    from app.application.runtime_settings_service import get_runtime_settings
    from app.domain.classification.pipeline import ClassificationPipeline
    from app.domain.classification.rule_engine import Rule
    from app.infrastructure.ai.agents.classification_agent import ClassificationAgent
    from app.infrastructure.ai.factory import create_llm_client
    from app.infrastructure.persistence.models.orm_models import CategoryRuleORM

    orm_rules = db.scalars(
        select(CategoryRuleORM)
        .where(CategoryRuleORM.user_id == user_id)
        .order_by(CategoryRuleORM.priority.desc())
    ).all()

    user_rules = [
        Rule(
            keywords=[r.match_value],
            category_l1=r.category_l1,
            category_l2=r.category_l2,
            priority=r.priority,
            match_field=r.match_field,
        )
        for r in orm_rules
    ]

    agent = None
    max_concurrency = 1
    try:
        runtime = get_runtime_settings(db, user_id)
        provider = runtime.llm_provider if runtime else None
        model = runtime.llm_model if runtime else None
        api_key = None
        base_url = None
        batch_size = None
        if runtime:
            max_concurrency = max(1, runtime.llm_max_concurrency)
            batch_size = max(1, runtime.llm_batch_size)
            if runtime.llm_provider == "deepseek":
                api_key = runtime.deepseek_api_key or None
                base_url = runtime.llm_base_url or None
            else:
                api_key = runtime.anthropic_api_key or None

        llm_client = create_llm_client(provider=provider, api_key=api_key, base_url=base_url, model=model)
        agent = ClassificationAgent(llm_client, user_rules=user_rules, batch_size=batch_size)
    except Exception as e:
        logger.warning("LLM classifier not available: %s", e)

    pipeline = ClassificationPipeline(llm_classifier=None, user_rules=user_rules)
    return pipeline, agent, max_concurrency


def _build_classification_stage_message(
    *,
    processed_rows: int,
    total_rows: int,
    llm_completed_batches: int,
    llm_total_batches: int,
) -> str:
    if llm_total_batches:
        return (
            f"正在进行 AI 分类（已处理 {processed_rows}/{total_rows} 条，"
            f"LLM 批次 {llm_completed_batches}/{llm_total_batches}）"
        )
    return f"正在进行 AI 分类（已处理 {processed_rows}/{total_rows} 条）"
