"""
Celery task: process a bill import end-to-end.
  1. Parse file → RawTransactions
  2. Bulk insert to DB
  3. Run classification pipeline
  4. Generate Beancount entries
  5. Update import status
"""
import logging

from app.infrastructure.queue.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="import_tasks.process_bill_import", bind=True, max_retries=3)
def process_bill_import(self, import_id: str, file_path: str, user_id: str) -> dict:
    """Main import pipeline task."""
    from app.infrastructure.persistence.database import SessionLocal
    from app.infrastructure.persistence.repositories import transaction_repo as repo
    from app.infrastructure.parsers import registry as parser_registry
    from app.domain.classification.pipeline import ClassificationPipeline
    from app.domain.beancount.engine import BeancountEngine
    from app.domain.transaction.models import Transaction, BillSource, TransactionDirection, CategorySource

    db = SessionLocal()
    try:
        repo.update_import_status(db, import_id, "processing")

        # 1. Read and parse file
        source_type, raw_transactions = parser_registry.parse_file(file_path)
        logger.info("Parsed %d transactions from %s", len(raw_transactions), source_type)

        if not raw_transactions:
            repo.update_import_status(db, import_id, "done", row_count=0)
            return {"import_id": import_id, "count": 0}

        # 2. Bulk insert
        inserted_transactions = repo.bulk_create_transactions(db, import_id, user_id, raw_transactions)
        repo.update_import_status(db, import_id, "classifying", row_count=len(inserted_transactions))

        if not inserted_transactions:
            repo.update_import_status(db, import_id, "done", row_count=0)
            logger.info("Import %s complete: all %d transactions were duplicates", import_id, len(raw_transactions))
            return {"import_id": import_id, "count": 0}

        # 3. Classification
        pipeline = _build_pipeline(db, user_id)
        beancount_engine = BeancountEngine()

        classified_count = 0
        for raw_tx, tx_id in inserted_transactions:
            result = pipeline.classify(raw_tx)
            repo.update_transaction_category(
                db,
                tx_id,
                result.category_l1,
                result.category_l2,
                result.source.value,
                confidence=result.confidence,
            )

            # 4. Beancount entry
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
                postings = [{"account": p.account, "amount": str(p.amount), "currency": p.currency}
                            for p in entry.postings]
                repo.save_beancount_entry(
                    db, tx_id, user_id, entry.date, entry.render(), postings
                )
            except Exception as e:
                logger.warning("Beancount entry generation failed for %s: %s", tx_id, e)

            classified_count += 1

        repo.update_import_status(db, import_id, "done", row_count=len(inserted_transactions))
        logger.info("Import %s complete: %d transactions", import_id, classified_count)
        return {"import_id": import_id, "count": classified_count}

    except Exception as exc:
        logger.exception("Import task failed for %s", import_id)
        repo.update_import_status(db, import_id, "failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


def _build_pipeline(db, user_id: str):
    """Build classification pipeline with user rules loaded from DB."""
    from sqlalchemy import select
    from app.infrastructure.persistence.models.orm_models import CategoryRuleORM
    from app.domain.classification.rule_engine import Rule
    from app.domain.classification.pipeline import ClassificationPipeline

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

    # Try to build LLM classifier
    llm_classifier = None
    try:
        from app.infrastructure.ai.factory import create_llm_client
        from app.infrastructure.ai.agents.classification_agent import ClassificationAgent
        from app.domain.classification.pipeline import ClassificationResult
        from app.domain.transaction.models import CategorySource

        agent = ClassificationAgent(create_llm_client(), user_rules=user_rules)
        _cache: list = []

        def llm_classify_single(tx):
            results = agent.classify_batch([tx])
            return results[0] if results else None

        llm_classifier = llm_classify_single
    except Exception as e:
        logger.warning("LLM classifier not available: %s", e)

    pipeline = ClassificationPipeline(llm_classifier=llm_classifier, user_rules=user_rules)
    return pipeline
