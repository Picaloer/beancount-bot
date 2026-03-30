from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from app.domain.classification.pipeline import ClassificationResult, ClassificationPipeline
from app.domain.transaction.models import CategorySource, RawTransaction
from app.infrastructure.ai.agents.classification_agent import ClassificationAgent
from app.infrastructure.ai.base import LLMUsage


@dataclass
class BatchClassificationResult:
    results: list[ClassificationResult]
    processed_rows: int
    llm_batches: int
    usage: LLMUsage


@dataclass
class BatchProgressUpdate:
    processed_rows: int
    llm_completed_batches: int
    usage: LLMUsage


def classify_transactions(
    transactions: list[RawTransaction],
    pipeline: ClassificationPipeline,
    agent: ClassificationAgent | None,
    max_concurrency: int,
    progress_callback: Callable[[BatchProgressUpdate], None] | None = None,
) -> BatchClassificationResult:
    if not transactions:
        return BatchClassificationResult(results=[], processed_rows=0, llm_batches=0, usage=LLMUsage())

    if agent is None:
        results = [pipeline.classify(tx) for tx in transactions]
        if progress_callback:
            progress_callback(
                BatchProgressUpdate(
                    processed_rows=len(results),
                    llm_completed_batches=0,
                    usage=LLMUsage(),
                )
            )
        return BatchClassificationResult(results=results, processed_rows=len(results), llm_batches=0, usage=LLMUsage())

    preliminary: list[ClassificationResult | None] = []
    llm_candidates: list[tuple[int, RawTransaction]] = []
    processed_rows = 0

    for index, tx in enumerate(transactions):
        rule_result = _classify_without_llm(pipeline, tx)
        if rule_result is None:
            preliminary.append(None)
            llm_candidates.append((index, tx))
        else:
            preliminary.append(rule_result)
            processed_rows += 1

    usage = LLMUsage()
    llm_completed_batches = 0
    if progress_callback and processed_rows > 0:
        progress_callback(
            BatchProgressUpdate(
                processed_rows=processed_rows,
                llm_completed_batches=0,
                usage=LLMUsage(),
            )
        )

    if not llm_candidates:
        return BatchClassificationResult(
            results=[result for result in preliminary if result is not None],
            processed_rows=len(transactions),
            llm_batches=0,
            usage=LLMUsage(),
        )

    indexed_batches = [llm_candidates[i: i + agent.batch_size] for i in range(0, len(llm_candidates), agent.batch_size)]

    with ThreadPoolExecutor(max_workers=max(1, max_concurrency)) as executor:
        futures = {
            executor.submit(agent.classify_with_usage, [tx for _, tx in batch]): batch
            for batch in indexed_batches
        }
        for future in as_completed(futures):
            batch = futures[future]
            completion = future.result()
            usage.input_tokens += completion.usage.input_tokens
            usage.output_tokens += completion.usage.output_tokens
            llm_completed_batches += 1
            processed_rows += len(batch)
            for (index, _), result in zip(batch, completion.results, strict=False):
                preliminary[index] = result
            if progress_callback:
                progress_callback(
                    BatchProgressUpdate(
                        processed_rows=processed_rows,
                        llm_completed_batches=llm_completed_batches,
                        usage=LLMUsage(
                            input_tokens=usage.input_tokens,
                            output_tokens=usage.output_tokens,
                        ),
                    )
                )

    final_results = [result or ClassificationResult("其他", "未分类", 0.0, CategorySource.FALLBACK) for result in preliminary]
    return BatchClassificationResult(
        results=final_results,
        processed_rows=len(final_results),
        llm_batches=len(indexed_batches),
        usage=usage,
    )


def _classify_without_llm(pipeline: ClassificationPipeline, tx: RawTransaction) -> ClassificationResult | None:
    return pipeline.classify_before_llm(tx)
