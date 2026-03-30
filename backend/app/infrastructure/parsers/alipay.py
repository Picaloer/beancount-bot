"""
Alipay CSV bill parser.

File format (UTF-8 with BOM, GBK also possible):
  Line 1:  支付宝交易记录明细查询
  Line 2-4: metadata
  Line N:  CSV header with trailing spaces: 交易号 ,商家订单号 , ...
  Data rows follow
  EOF marker: ----------------------------

Columns: 交易号,商家订单号,交易创建时间,付款时间,最近修改时间,交易来源地,类型,
          交易对方,商品名称,金额（元）,收/支,交易状态,服务费（元）,退款（元）,备注,资金状态
"""
import csv
import io
import logging
from datetime import datetime

from app.domain.transaction.models import BillSource, RawTransaction, TransactionDirection
from app.infrastructure.parsers.base import BillParserAdapter
from app.infrastructure.parsers.registry import register

logger = logging.getLogger(__name__)

ALIPAY_SIGNATURES = ("支付宝交易记录", "支付宝支付科技")
# Old format header starts with "交易号"; new format starts with "交易时间,交易分类"
ALIPAY_HEADER_KEYWORDS = ("交易号", "交易时间,交易分类")

DIRECTION_MAP = {
    "支出": TransactionDirection.EXPENSE,
    "收入": TransactionDirection.INCOME,
    "不计收支": TransactionDirection.TRANSFER,
}

SUCCESS_STATUSES = {"交易成功", "支付成功", "已完成"}


def _is_header_line(line: str) -> bool:
    stripped = line.strip().replace(" ", "")
    return any(stripped.startswith(keyword) for keyword in ALIPAY_HEADER_KEYWORDS)


class AlipayParser(BillParserAdapter):
    @property
    def source_type(self) -> str:
        return "alipay"

    def can_parse(self, content: str) -> bool:
        if any(signature in content for signature in ALIPAY_SIGNATURES):
            return True
        return any(_is_header_line(line) for line in content.splitlines())

    def parse(self, content: str) -> list[RawTransaction]:
        content = content.lstrip("\ufeff")

        lines = content.splitlines()
        header_idx = None
        for i, line in enumerate(lines):
            if _is_header_line(line):
                header_idx = i
                break

        if header_idx is None:
            logger.warning("Alipay parser: header row not found")
            return []

        # Collect data lines until EOF marker
        data_lines: list[str] = [lines[header_idx]]
        for line in lines[header_idx + 1:]:
            if line.startswith("---"):
                break
            data_lines.append(line)

        csv_text = "\n".join(data_lines)
        reader = csv.DictReader(io.StringIO(csv_text))
        reader.fieldnames = [f.strip() for f in (reader.fieldnames or [])]

        transactions: list[RawTransaction] = []
        for row in reader:
            try:
                normalized_row = {k.strip(): (v or "").strip() for k, v in row.items() if k}
                tx = self._parse_row(normalized_row)
                if tx:
                    transactions.append(tx)
            except Exception as e:
                logger.debug("Skipping Alipay row: %s | error: %s", row, e)

        logger.info("Alipay parser: parsed %d transactions", len(transactions))
        return transactions

    def _parse_row(self, row: dict) -> RawTransaction | None:
        status = row.get("交易状态", "")
        if not any(s in status for s in SUCCESS_STATUSES):
            return None

        direction_str = row.get("收/支", "不计收支")
        direction = DIRECTION_MAP.get(direction_str, TransactionDirection.TRANSFER)

        amount_str = (row.get("金额（元）") or row.get("金额") or "0").replace(",", "").strip()
        amount = float(amount_str)

        dt_str = row.get("付款时间", "") or row.get("交易创建时间", "") or row.get("交易时间", "")
        try:
            transaction_at = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            transaction_at = datetime.now()

        merchant = row.get("交易对方", "")
        description = row.get("商品名称", "") or row.get("商品说明", "")

        return RawTransaction(
            source=BillSource.ALIPAY,
            direction=direction,
            amount=amount,
            currency="CNY",
            merchant=merchant,
            description=description,
            transaction_at=transaction_at,
            raw_data=dict(row),
            external_id=(row.get("交易订单号", "") or row.get("交易号", "") or None),
        )


register(AlipayParser())
