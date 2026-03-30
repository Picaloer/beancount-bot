"""
LLM-based batch classification agent.
Groups transactions into batches and classifies them with Claude.
Returns ClassificationResult per transaction.
"""
import json
import logging

from app.core.config import settings
from app.domain.classification.category_tree import category_tree_for_prompt
from app.domain.classification.pipeline import ClassificationResult
from app.domain.transaction.models import CategorySource, RawTransaction
from app.infrastructure.ai.agents.base import AgentResult
from app.infrastructure.ai.base import LLMAdapter, LLMMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的个人财务分类助手。
请根据交易信息，将每笔交易分类到合适的一级和二级分类中。

分类体系:
{category_tree}

规则:
1. 每笔交易必须有一级分类(category_l1)，尽量给出二级分类(category_l2)
2. 如果无法确定二级分类，category_l2 填 null
3. confidence 范围 0.0-1.0，表示分类可信度
4. 严格返回 JSON 数组，不要有任何额外文字

返回格式:
[
  {{"id": "交易ID", "category_l1": "餐饮", "category_l2": "外卖", "confidence": 0.95}},
  ...
]"""


class ClassificationAgent:
    agent_id = "classification"
    description = "LLM-based transaction category classification"

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm
        self._batch_size = settings.llm_batch_size

    def classify_batch(self, transactions: list[RawTransaction]) -> list[ClassificationResult]:
        """Classify a batch of transactions. Returns one result per transaction."""
        results: list[ClassificationResult] = []

        # Process in sub-batches
        for i in range(0, len(transactions), self._batch_size):
            batch = transactions[i: i + self._batch_size]
            batch_results = self._classify_sub_batch(batch)
            results.extend(batch_results)

        return results

    def _classify_sub_batch(self, batch: list[RawTransaction]) -> list[ClassificationResult]:
        items = [
            {"id": str(idx), "merchant": tx.merchant, "description": tx.description, "amount": tx.amount}
            for idx, tx in enumerate(batch)
        ]
        system = SYSTEM_PROMPT.format(category_tree=category_tree_for_prompt())
        user_content = f"请对以下交易进行分类:\n{json.dumps(items, ensure_ascii=False)}"

        try:
            response_text = self._llm.complete(
                messages=[LLMMessage(role="user", content=user_content)],
                system=system,
            )
            return self._parse_response(response_text, len(batch))
        except Exception as e:
            logger.error("Classification LLM call failed: %s", e)
            # Return fallback for entire batch
            return [
                ClassificationResult("其他", "未分类", 0.0, CategorySource.FALLBACK)
                for _ in batch
            ]

    def _parse_response(self, text: str, expected_count: int) -> list[ClassificationResult]:
        # Extract JSON from response (handle markdown code blocks)
        text = text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Could not parse LLM classification response as JSON")
            return [
                ClassificationResult("其他", "未分类", 0.0, CategorySource.FALLBACK)
                for _ in range(expected_count)
            ]

        results: list[ClassificationResult] = []
        for item in data:
            confidence = float(item.get("confidence", 0.8))
            results.append(
                ClassificationResult(
                    category_l1=item.get("category_l1", "其他"),
                    category_l2=item.get("category_l2"),
                    confidence=confidence,
                    source=CategorySource.LLM if confidence >= 0.5 else CategorySource.FALLBACK,
                )
            )

        # Pad with fallback if LLM returned fewer items than expected
        while len(results) < expected_count:
            results.append(ClassificationResult("其他", "未分类", 0.0, CategorySource.FALLBACK))

        return results[:expected_count]
