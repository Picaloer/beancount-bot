"""Natural-language financial query service."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.classification.category_tree import L1_CATEGORIES
from app.infrastructure.persistence.models.orm_models import TransactionORM


@dataclass
class ParsedQuery:
    intent: str
    year_month: str
    category_l1: str | None = None


def answer_question(db: Session, user_id: str, question: str) -> dict:
    text = question.strip()
    if not text:
        raise ValueError("问题不能为空")

    parsed = ParsedQuery(
        intent=_detect_intent(text),
        year_month=_resolve_year_month(db, user_id, text),
        category_l1=_extract_category(text),
    )

    if parsed.intent == "category_total" and not parsed.category_l1:
        raise ValueError("请在问题里带上一级分类，例如餐饮、交通、住房")

    return _run_query(db, user_id, text, parsed)


def _run_query(db: Session, user_id: str, question: str, parsed: ParsedQuery) -> dict:
    start, end = _month_bounds(parsed.year_month)
    month_label = _format_month_label(parsed.year_month)

    if parsed.intent == "total_expense":
        total, count = _sum_and_count(db, user_id, start, end, direction="expense")
        return {
            "question": question,
            "intent": parsed.intent,
            "year_month": parsed.year_month,
            "answer": f"{month_label}总支出 {format_currency(total)}，共 {count} 笔支出。",
            "data": {"total": round(total, 2), "count": count},
        }

    if parsed.intent == "total_income":
        total, count = _sum_and_count(db, user_id, start, end, direction="income")
        return {
            "question": question,
            "intent": parsed.intent,
            "year_month": parsed.year_month,
            "answer": f"{month_label}总收入 {format_currency(total)}，共 {count} 笔收入。",
            "data": {"total": round(total, 2), "count": count},
        }

    if parsed.intent == "net":
        income_total, income_count = _sum_and_count(db, user_id, start, end, direction="income")
        expense_total, expense_count = _sum_and_count(db, user_id, start, end, direction="expense")
        net = income_total - expense_total
        return {
            "question": question,
            "intent": parsed.intent,
            "year_month": parsed.year_month,
            "answer": (
                f"{month_label}净收支 {format_currency(net)}，"
                f"收入 {format_currency(income_total)}，支出 {format_currency(expense_total)}。"
            ),
            "data": {
                "net": round(net, 2),
                "income_total": round(income_total, 2),
                "income_count": income_count,
                "expense_total": round(expense_total, 2),
                "expense_count": expense_count,
            },
        }

    if parsed.intent == "transaction_count":
        count = db.scalar(
            select(func.count())
            .select_from(TransactionORM)
            .where(
                TransactionORM.user_id == user_id,
                TransactionORM.transaction_at >= start,
                TransactionORM.transaction_at < end,
            )
        ) or 0
        return {
            "question": question,
            "intent": parsed.intent,
            "year_month": parsed.year_month,
            "answer": f"{month_label}共有 {count} 笔交易。",
            "data": {"count": count},
        }

    if parsed.intent == "category_total":
        total, count = _sum_and_count(
            db,
            user_id,
            start,
            end,
            direction="expense",
            category_l1=parsed.category_l1,
        )
        return {
            "question": question,
            "intent": parsed.intent,
            "year_month": parsed.year_month,
            "answer": (
                f"{month_label}{parsed.category_l1}支出 {format_currency(total)}，"
                f"共 {count} 笔。"
            ),
            "data": {
                "category_l1": parsed.category_l1,
                "total": round(total, 2),
                "count": count,
            },
        }

    if parsed.intent == "top_category":
        row = db.execute(
            select(
                TransactionORM.category_l1,
                func.sum(TransactionORM.amount).label("total"),
                func.count().label("count"),
            )
            .where(
                TransactionORM.user_id == user_id,
                TransactionORM.direction == "expense",
                TransactionORM.transaction_at >= start,
                TransactionORM.transaction_at < end,
            )
            .group_by(TransactionORM.category_l1)
            .order_by(func.sum(TransactionORM.amount).desc())
            .limit(1)
        ).first()

        if not row:
            return _empty_answer(question, parsed, f"{month_label}暂无可统计的支出数据。")

        return {
            "question": question,
            "intent": parsed.intent,
            "year_month": parsed.year_month,
            "answer": (
                f"{month_label}支出最多的分类是 {row.category_l1}，"
                f"共 {format_currency(float(row.total))}，{row.count} 笔。"
            ),
            "data": {
                "category_l1": row.category_l1,
                "total": round(float(row.total), 2),
                "count": row.count,
            },
        }

    if parsed.intent == "top_merchant":
        row = db.execute(
            select(
                TransactionORM.merchant,
                func.sum(TransactionORM.amount).label("total"),
                func.count().label("count"),
            )
            .where(
                TransactionORM.user_id == user_id,
                TransactionORM.direction == "expense",
                TransactionORM.merchant != "",
                TransactionORM.transaction_at >= start,
                TransactionORM.transaction_at < end,
            )
            .group_by(TransactionORM.merchant)
            .order_by(func.sum(TransactionORM.amount).desc())
            .limit(1)
        ).first()

        if not row:
            return _empty_answer(question, parsed, f"{month_label}暂无可统计的商家支出数据。")

        return {
            "question": question,
            "intent": parsed.intent,
            "year_month": parsed.year_month,
            "answer": (
                f"{month_label}花得最多的商家是 {row.merchant}，"
                f"共 {format_currency(float(row.total))}，{row.count} 笔。"
            ),
            "data": {
                "merchant": row.merchant,
                "total": round(float(row.total), 2),
                "count": row.count,
            },
        }

    raise ValueError("暂不支持这个问题，请试试总支出、收入、分类支出或最多消费分类")


def _sum_and_count(
    db: Session,
    user_id: str,
    start: datetime,
    end: datetime,
    direction: str,
    category_l1: str | None = None,
) -> tuple[float, int]:
    conditions = [
        TransactionORM.user_id == user_id,
        TransactionORM.direction == direction,
        TransactionORM.transaction_at >= start,
        TransactionORM.transaction_at < end,
    ]
    if category_l1:
        conditions.append(TransactionORM.category_l1 == category_l1)

    total = db.scalar(
        select(func.coalesce(func.sum(TransactionORM.amount), 0))
        .select_from(TransactionORM)
        .where(*conditions)
    )
    count = db.scalar(
        select(func.count())
        .select_from(TransactionORM)
        .where(*conditions)
    )
    return float(total or 0), int(count or 0)


def _detect_intent(text: str) -> str:
    if _contains_any(text, ["哪个商家", "哪家商家", "商家花得最多", "商家支出最多", "最多的商家"]):
        return "top_merchant"

    if _contains_any(text, ["哪个类别", "哪个分类", "哪类支出", "哪个项目"]) and _contains_any(
        text, ["最多", "最高", "最大", "超支"]
    ):
        return "top_category"

    if _contains_any(text, ["净收支", "结余", "净额", "净流入", "净流出"]):
        return "net"

    if _contains_any(text, ["多少笔", "几笔", "交易数", "交易笔数"]):
        return "transaction_count"

    category = _extract_category(text)
    if category and _contains_any(text, ["花", "支出", "消费", "开销", "多少钱", "多少"]):
        return "category_total"

    if "收入" in text:
        return "total_income"

    if _contains_any(text, ["花了多少", "支出多少", "消费多少", "开销多少", "总支出", "支出总额"]):
        return "total_expense"

    if category:
        return "category_total"

    if _contains_any(text, ["花了", "支出", "消费", "开销"]):
        return "total_expense"

    raise ValueError("暂时支持查询总支出、总收入、净收支、分类支出、最高支出分类、最高支出商家和交易笔数")


def _resolve_year_month(db: Session, user_id: str, text: str) -> str:
    explicit = re.search(r"(20\d{2})[-年/.](\d{1,2})", text)
    if explicit:
        year = int(explicit.group(1))
        month = int(explicit.group(2))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    reference = _latest_year_month(db, user_id)
    if _contains_any(text, ["上个月", "上月"]):
        return _shift_year_month(reference, -1)
    if _contains_any(text, ["这个月", "本月", "当月", "最近一个月"]):
        return reference
    return reference


def _latest_year_month(db: Session, user_id: str) -> str:
    latest = db.scalar(
        select(func.max(TransactionORM.transaction_at)).where(TransactionORM.user_id == user_id)
    )
    if latest:
        return latest.strftime("%Y-%m")
    return datetime.utcnow().strftime("%Y-%m")


def _extract_category(text: str) -> str | None:
    matches = [(text.find(category), category) for category in L1_CATEGORIES if category in text]
    matches = [match for match in matches if match[0] >= 0]
    if not matches:
        return None
    matches.sort(key=lambda item: item[0])
    return matches[0][1]


def _month_bounds(year_month: str) -> tuple[datetime, datetime]:
    year, month = map(int, year_month.split("-"))
    start = datetime(year, month, 1)
    end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
    return start, end


def _shift_year_month(year_month: str, delta: int) -> str:
    year, month = map(int, year_month.split("-"))
    month += delta
    while month <= 0:
        year -= 1
        month += 12
    while month > 12:
        year += 1
        month -= 12
    return f"{year:04d}-{month:02d}"


def _format_month_label(year_month: str) -> str:
    year, month = year_month.split("-")
    return f"{year}年{month}月"


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _empty_answer(question: str, parsed: ParsedQuery, answer: str) -> dict:
    return {
        "question": question,
        "intent": parsed.intent,
        "year_month": parsed.year_month,
        "answer": answer,
        "data": {},
    }


def format_currency(value: float) -> str:
    return f"¥{value:,.2f}"
