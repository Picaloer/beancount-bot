import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.parsers.cmb import ChinaMerchantsBankPdfParser
from app.infrastructure.parsers.registry import auto_detect_file


PDF_PATH = Path(
    "/home/pica/assets/githubs/beancount-bot/backend/uploads/招商银行交易流水(申请时间2026年03月30日09时35分15秒).pdf"
)
WECHAT_XLSX_PATH = Path(
    "/home/pica/assets/githubs/beancount-bot/backend/uploads/微信支付账单流水文件(20250331-20260330)_20260330093731.xlsx"
)
ALIPAY_CSV_PATH = Path(
    "/home/pica/assets/githubs/beancount-bot/backend/uploads/支付宝交易明细(20250331-20260330).csv"
)


def test_cmb_pdf_auto_detects_and_parses_transactions():
    parser = auto_detect_file(PDF_PATH)

    assert parser.source_type == "cmb"

    transactions = parser.parse_file(PDF_PATH)
    assert len(transactions) == 227

    first = transactions[0]
    assert first.source.value == "cmb"
    assert first.direction.value == "income"
    assert first.amount == 1001.00
    assert first.currency == "CNY"
    assert first.merchant == "刘昊"
    assert first.description == "网联收款"
    assert first.raw_data["联机余额"] == "1,001.00"

    last = transactions[-1]
    assert last.direction.value == "expense"
    assert last.amount == 49.81
    assert last.merchant == "杭州深度求索"
    assert last.description == "快捷支付"


def test_cmb_pdf_parser_prefers_direct_text_extraction():
    parser = ChinaMerchantsBankPdfParser()

    text = parser._extract_pdf_text(PDF_PATH)

    assert "招商银行交易流水" in text
    assert "北京常营支行" in text
    assert "杭州深度求索" in text


def test_existing_user_samples_still_auto_detect():
    assert auto_detect_file(WECHAT_XLSX_PATH).source_type == "wechat"
    assert auto_detect_file(ALIPAY_CSV_PATH).source_type == "alipay"
