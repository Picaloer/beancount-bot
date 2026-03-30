"""
Celery task: process a bill import end-to-end.
  1. Parse file → RawTransactions
  2. Bulk insert to DB
  3. Run classification pipeline
  4. Generate Beancount entries
  5. Update import status
"""
import logging

from app.core.timezone import now_beijing
from app.domain.classification.batch_runner import BatchProgressUpdate, classify_transactions
from app.infrastructure.queue.celery_app import celery_app

logger = logging.getLogger(__name__)


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
                finished_at=now_beijing(),
            )
            repo.update_import_stage(
                db,
                import_id,
                "dedupe",
                status="done",
                message="无需去重，没有可导入交易",
                finished_at=now_beijing(),
            )
            repo.update_import_stage(
                db,
                import_id,
                "classify",
                status="done",
                message="无需分类，没有可导入交易",
                finished_at=now_beijing(),
            )
            repo.update_import_stage(
                db,
                import_id,
                "beancount",
                status="done",
                message="无需生成分录，没有可导入交易",
                finished_at=now_beijing(),
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

        if not inserted_transactions:
            duplicate_finished_at = now_beijing()
            repo.update_import_stage(
                db,
                import_id,
                "classify",
                status="done",
                message="无需分类，全部为重复交易",
                finished_at=duplicate_finished_at,
            )
            repo.update_import_stage(
                db,
                import_id,
                "beancount",
                status="done",
                message="无需生成分录，全部为重复交易",
                finished_at=duplicate_finished_at,
            )
            repo.update_import_status(
                db,
                import_id,
                status="done",
                row_count=0,
                processed_rows=0,
                llm_total_batches=0,
                llm_completed_batches=0,
                stage_message="导入完成，全部为重复交易",
                finished_at=duplicate_finished_at,
            )
            repo.update_import_summary(
                db,
                import_id,
                inserted_count=0,
                duplicate_count=len(raw_transactions),
                beancount_entry_count=0,
                rule_based_count=0,
                llm_based_count=0,
                fallback_count=0,
                low_confidence_count=0,
            )
            logger.info("Import %s complete: all %d transactions were duplicates", import_id, len(raw_transactions))
            return {"import_id": import_id, "count": 0}

        pipeline, agent, max_concurrency = _build_pipeline(db, user_id)
        llm_batch_size = agent.batch_size if agent else 0
        llm_candidate_count = (
            sum(1 for raw_tx, _ in inserted_transactions if pipeline.classify_before_llm(raw_tx) is None)
            if agent and llm_batch_size
            else 0
        )
        llm_total_batches = ((llm_candidate_count - 1) // llm_batch_size + 1) if llm_candidate_count else 0
        repo.update_import_status(
            db,
            import_id,
            status="classifying",
            row_count=len(inserted_transactions),
            llm_total_batches=llm_total_batches,
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
                    total_rows=len(inserted_transactions),
                    llm_completed_batches=update.llm_completed_batches,
                    llm_total_batches=llm_total_batches,
                ),
            )

        batch_result = classify_transactions(
            [raw_tx for raw_tx, _ in inserted_transactions],
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
            inserted_count=len(inserted_transactions),
            duplicate_count=duplicate_count,
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
        classified_count = 0
        beancount_entry_count = 0
        beancount_started_at = now_beijing()
        repo.update_import_stage(
            db,
            import_id,
            "beancount",
            status="processing",
            message="正在生成 Beancount 分录",
            started_at=beancount_started_at,
        )
        for (raw_tx, tx_id), result in zip(inserted_transactions, batch_result.results, strict=False):
            repo.update_transaction_category(
                db,
                tx_id,
                result.category_l1,
                result.category_l2,
                result.source.value,
                confidence=result.confidence,
            )

            domain_tx = Transaction(
                id=tx_id,
                user_id=user_id,
                import_id=import_id,
                source=raw_tx.source,
                direction=raw_tx.direction,
                amount=raw_tx.amount,
                currency=raw_tx.currency,
                merchant=raw_tx.merchant,
                description=raw_tx.description,
                transaction_at=raw_tx.transaction_at,
                category_l1=result.category_l1,
                category_l2=result.category_l2,
                category_source=result.source,
            )
            try:
                entry = beancount_engine.generate_entry(domain_tx)
                postings = [
                    {"account": p.account, "amount": str(p.amount), "currency": p.currency}
                    for p in entry.postings
                ]
                repo.save_beancount_entry(db, tx_id, user_id, entry.date, entry.render(), postings)
                beancount_entry_count += 1
            except Exception as e:
                logger.warning("Beancount entry generation failed for %s: %s", tx_id, e)

            classified_count += 1

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
            row_count=len(inserted_transactions),
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
            inserted_count=len(inserted_transactions),
            duplicate_count=duplicate_count,
            beancount_entry_count=beancount_entry_count,
            rule_based_count=rule_based_count,
            llm_based_count=llm_based_count,
            fallback_count=fallback_count,
            low_confidence_count=low_confidence_count,
        )
        logger.info("Import %s complete: %d transactions", import_id, classified_count)
        return {"import_id": import_id, "count": classified_count}

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
        for stage_key in ("parse", "dedupe", "classify", "beancount"):
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


def _build_classification_stage_message(
    *,
    processed_rows: int,
    total_rows: int,
    llm_completed_batches: int,
    llm_total_batches: int,
) -> str:
    if llm_total_batches > 0:
        return (
            f"AI 分类中：已完成 {processed_rows}/{total_rows} 条交易"
            f"（批次 {llm_completed_batches}/{llm_total_batches}）"
        )
    return f"正在应用规则分类：已完成 {processed_rows}/{total_rows} 条交易"


def _build_pipeline(db, user_id: str):
    """Build classification pipeline with user rules loaded from DB."""
    from sqlalchemy import select

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
