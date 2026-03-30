"""
Classification pipeline using Chain of Responsibility.

Priority order:
  1. UserDefinedRuleStage  — user's custom keyword rules
  2. SystemRuleStage       — built-in 500+ merchant rules
  3. LLMStage              — Claude API batch classification
  4. FallbackStage         — default to '其他 / 未分类'

Each stage returns a ClassificationResult or None (pass to next stage).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from app.domain.transaction.models import CategorySource, RawTransaction

if TYPE_CHECKING:
    from app.domain.classification.rule_engine import Rule, RuleEngine


@dataclass
class ClassificationResult:
    category_l1: str
    category_l2: str | None
    confidence: float
    source: CategorySource


class ClassificationStage(ABC):
    @abstractmethod
    def classify(self, tx: RawTransaction) -> ClassificationResult | None:
        """Return None to pass to the next stage."""


class UserDefinedRuleStage(ClassificationStage):
    def __init__(self, user_rules: list | None = None) -> None:
        from app.domain.classification.rule_engine import RuleEngine
        self._engine = RuleEngine(rules=user_rules or [])

    def classify(self, tx: RawTransaction) -> ClassificationResult | None:
        result = self._engine.classify(tx)
        if result:
            return ClassificationResult(*result, confidence=1.0, source=CategorySource.USER_RULE)
        return None


class SystemRuleStage(ClassificationStage):
    def __init__(self) -> None:
        from app.domain.classification.rule_engine import RuleEngine, SYSTEM_RULES
        self._engine = RuleEngine(rules=SYSTEM_RULES)

    def classify(self, tx: RawTransaction) -> ClassificationResult | None:
        result = self._engine.classify(tx)
        if result:
            return ClassificationResult(*result, confidence=0.95, source=CategorySource.SYSTEM_RULE)
        return None


class LLMStage(ClassificationStage):
    """Delegates to an injected LLM classifier callable."""

    def __init__(self, llm_classifier=None) -> None:
        self._llm_classifier = llm_classifier  # set by DI after init

    def classify(self, tx: RawTransaction) -> ClassificationResult | None:
        if self._llm_classifier is None:
            return None
        return self._llm_classifier(tx)


class FallbackStage(ClassificationStage):
    def classify(self, tx: RawTransaction) -> ClassificationResult | None:
        return ClassificationResult(
            category_l1="其他",
            category_l2="未分类",
            confidence=0.0,
            source=CategorySource.FALLBACK,
        )


class ClassificationPipeline:
    def __init__(self, llm_classifier=None, user_rules: list | None = None) -> None:
        self._llm_stage = LLMStage(llm_classifier)
        self._stages: list[ClassificationStage] = [
            UserDefinedRuleStage(user_rules),
            SystemRuleStage(),
            self._llm_stage,
            FallbackStage(),
        ]

    def set_llm_classifier(self, classifier) -> None:
        self._llm_stage._llm_classifier = classifier

    def classify(self, tx: RawTransaction) -> ClassificationResult:
        for stage in self._stages:
            result = stage.classify(tx)
            if result is not None:
                return result
        # Should never reach here (FallbackStage always returns)
        return ClassificationResult("其他", "未分类", 0.0, CategorySource.FALLBACK)

    def classify_before_llm(self, tx: RawTransaction) -> ClassificationResult | None:
        for stage in self._stages:
            if isinstance(stage, (LLMStage, FallbackStage)):
                return None
            result = stage.classify(tx)
            if result is not None:
                return result
        return None

    def classify_batch(self, transactions: list[RawTransaction]) -> list[ClassificationResult]:
        return [self.classify(tx) for tx in transactions]
