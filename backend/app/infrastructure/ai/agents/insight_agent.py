"""
Monthly financial insight agent.
Takes aggregated monthly statistics and generates personalized narrative.
"""
import json
import logging

from app.infrastructure.ai.agents.base import AgentResult
from app.infrastructure.ai.base import LLMAdapter, LLMMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个友善、专业的个人财务顾问。
根据用户的月度消费数据，生成一段简洁、有价值的财务洞察报告（300字以内）。

要求:
1. 语气亲切，避免说教
2. 突出本月最显著的消费特征
3. 与上月对比时指出有意义的变化
4. 给出1-2条具体可行的建议
5. 用中文回复，不需要标题，直接输出正文段落"""


class InsightAgent:
    agent_id = "insight"
    description = "Generate monthly financial insight narrative"

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    def run(self, monthly_stats: dict, prev_stats: dict | None = None) -> AgentResult:
        """
        monthly_stats: {
            year_month, total_expense, total_income,
            category_breakdown: [{category_l1, amount, percentage}],
            top_merchants: [{merchant, amount, count}],
        }
        """
        try:
            user_content = self._build_user_message(monthly_stats, prev_stats)
            insight = self._llm.complete(
                messages=[LLMMessage(role="user", content=user_content)],
                system=SYSTEM_PROMPT,
            )
            return AgentResult(success=True, data=insight.strip())
        except Exception as e:
            logger.error("InsightAgent failed: %s", e)
            return AgentResult(success=False, error=str(e))

    def _build_user_message(self, stats: dict, prev_stats: dict | None) -> str:
        parts = [
            f"月份: {stats.get('year_month')}",
            f"总支出: ¥{stats.get('total_expense', 0):.2f}",
            f"总收入: ¥{stats.get('total_income', 0):.2f}",
            "",
            "分类支出:",
        ]
        for cat in stats.get("category_breakdown", []):
            parts.append(
                f"  {cat['category_l1']}: ¥{cat['amount']:.2f} ({cat['percentage']:.1f}%)"
            )

        top_merchants = stats.get("top_merchants", [])[:5]
        if top_merchants:
            parts.append("\nTop商家:")
            for m in top_merchants:
                parts.append(f"  {m['merchant']}: ¥{m['amount']:.2f} ({m['count']}笔)")

        if prev_stats:
            prev_expense = prev_stats.get("total_expense", 0)
            curr_expense = stats.get("total_expense", 0)
            change = curr_expense - prev_expense
            pct = (change / prev_expense * 100) if prev_expense else 0
            sign = "+" if change >= 0 else ""
            parts.append(
                f"\n与上月对比: 支出{sign}{change:.2f}元 ({sign}{pct:.1f}%)"
            )

        return "\n".join(parts)
