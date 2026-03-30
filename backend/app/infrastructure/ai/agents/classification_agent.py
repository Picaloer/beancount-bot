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
from app.domain.classification.rule_engine import SYSTEM_RULES, Rule
from app.domain.transaction.models import CategorySource, RawTransaction
from app.infrastructure.ai.base import LLMAdapter, LLMMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的个人财务分类助手。请基于交易中的商户名、描述、金额方向与常见消费语义进行分类。

分类体系:
{category_tree}

已有规则分类器知识（仅作参考，不要机械照抄；如果规则明显不适用，可以拒绝跟随）:
{rule_knowledge}

分类原则:
1. 优先利用商户名和描述中的行业语义做判断，不要轻易归为“其他/未分类”。
2. 若商户明显属于某个行业，即使现有规则未命中，也应尽量归入最合理的一级/二级分类。
3. 只有在信息确实不足时才使用“其他 / 未分类”。
4. 如果无法确定二级分类，但能确定一级分类，则 category_l2 填该一级分类下最稳妥的兜底子类；若没有合适子类再填 null。
5. 转账、收款、还款、储蓄转移、红包等资金流转优先考虑“转账”而不是消费类目。
6. 云服务、软件订阅、开发平台、API 调用、会员订阅等优先考虑“数码服务”。
7. confidence 范围 0.0-1.0：
   - 0.9-1.0 = 非常确定
   - 0.7-0.89 = 较确定
   - 0.5-0.69 = 有一定依据但不完全确定
   - 0.0-0.49 = 证据不足，应尽量避免
8. 严格返回 JSON 数组，不要有任何额外文字。

返回格式:
[
  {{"id": "交易ID", "category_l1": "餐饮", "category_l2": "外卖", "confidence": 0.95}},
  ...
]"""


def _format_rule_knowledge(rules: list[Rule], title: str, limit: int) -> str:
    lines: list[str] = []
    for rule in rules[:limit]:
        keyword_preview = " / ".join(rule.keywords[:4])
        lines.append(
            f"- {title} | match_field={rule.match_field} | keywords={keyword_preview} => {rule.category_l1}/{rule.category_l2 or 'null'}"
        )
    if len(rules) > limit:
        lines.append(f"- {title} | ... 其余 {len(rules) - limit} 条规则省略")
    return "\n".join(lines)


class ClassificationAgent:
    agent_id = "classification"
    description = "LLM-based transaction category classification"

    def __init__(self, llm: LLMAdapter, user_rules: list[Rule] | None = None) -> None:
        self._llm = llm
        self._batch_size = settings.llm_batch_size
        self._user_rules = user_rules or []

    def classify_batch(self, transactions: list[RawTransaction]) -> list[ClassificationResult]:
        """Classify a batch of transactions. Returns one result per transaction."""
        results: list[ClassificationResult] = []

        for i in range(0, len(transactions), self._batch_size):
            batch = transactions[i: i + self._batch_size]
            batch_results = self._classify_sub_batch(batch)
            results.extend(batch_results)

        return results

    def _classify_sub_batch(self, batch: list[RawTransaction]) -> list[ClassificationResult]:
        items = [
            {
                "id": str(idx),
                "merchant": tx.merchant,
                "description": tx.description,
                "amount": tx.amount,
                "direction": tx.direction.value,
                "source": tx.source.value,
            }
            for idx, tx in enumerate(batch)
        ]
        system = SYSTEM_PROMPT.format(
            category_tree=category_tree_for_prompt(),
            rule_knowledge=self._build_rule_knowledge(),
        )
        user_content = f"请对以下交易进行分类:\n{json.dumps(items, ensure_ascii=False)}"

        try:
            response_text = self._llm.complete(
                messages=[LLMMessage(role="user", content=user_content)],
                system=system,
            )
            return self._parse_response(response_text, len(batch))
        except Exception as e:
            logger.error("Classification LLM call failed: %s", e)
            return [
                ClassificationResult("其他", "未分类", 0.0, CategorySource.FALLBACK)
                for _ in batch
            ]

    def _build_rule_knowledge(self) -> str:
        sections = []
        if self._user_rules:
            sections.append(_format_rule_knowledge(self._user_rules, "用户规则", limit=20))
        sections.append(_format_rule_knowledge(SYSTEM_RULES, "系统规则", limit=40))
        return "\n".join(section for section in sections if section)

    def _parse_response(self, text: str, expected_count: int) -> list[ClassificationResult]:
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

        while len(results) < expected_count:
            results.append(ClassificationResult("其他", "未分类", 0.0, CategorySource.FALLBACK))

        return results[:expected_count]
