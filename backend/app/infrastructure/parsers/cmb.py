"""
China Merchants Bank PDF statement parser.

Preferred strategy:
- extract embedded PDF text directly via PyMuPDF (best quality on real sample)
- fallback to RapidOCR on rendered page images when text extraction is unavailable
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import fitz

from app.domain.transaction.models import BillSource, RawTransaction, TransactionDirection
from app.infrastructure.parsers.base import BillParserAdapter
from app.infrastructure.parsers.registry import register

logger = logging.getLogger(__name__)

CMB_SIGNATURES = (
    "招商银行交易流水",
    "Transaction Statement of China Merchants Bank",
)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
AMOUNT_RE = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d{2})$|^-?\d+\.\d{2}$")
HEADER_SKIP_LINES = {
    "记账日期",
    "货币",
    "交易金额",
    "联机余额",
    "交易摘要",
    "对手信息",
    "Date",
    "Currency",
    "Transaction",
    "Amount",
    "Balance",
    "Transaction Type",
    "Counter Party",
    "温馨提示：",
}
TRAILING_NOTE_MARKERS = (
    "温馨提示",
    "交易流水验真",
)


class ChinaMerchantsBankPdfParser(BillParserAdapter):
    @property
    def source_type(self) -> str:
        return "cmb"

    def can_parse(self, content: str) -> bool:
        return any(signature in content for signature in CMB_SIGNATURES)

    def can_parse_file(self, file_path: Path) -> bool:
        if file_path.suffix.lower() != ".pdf":
            return False

        try:
            text = self._extract_pdf_text(file_path)
        except Exception:
            return False

        return self.can_parse(text)

    def parse(self, content: str) -> list[RawTransaction]:
        return self._parse_transactions(content)

    def parse_file(self, file_path: Path) -> list[RawTransaction]:
        text = self._extract_pdf_text(file_path)
        if not self.can_parse(text):
            raise ValueError("Unsupported China Merchants Bank PDF statement")
        transactions = self._parse_transactions(text)
        logger.info("CMB PDF parser: parsed %d transactions", len(transactions))
        return transactions

    def _extract_pdf_text(self, file_path: Path) -> str:
        text = self._extract_pdf_text_direct(file_path)
        if self.can_parse(text):
            return text

        logger.info("CMB PDF parser: direct text extraction empty, falling back to OCR")
        return self._extract_pdf_text_via_ocr(file_path)

    def _extract_pdf_text_direct(self, file_path: Path) -> str:
        doc = fitz.open(file_path)
        try:
            return "\n".join((doc.load_page(i).get_text() or "") for i in range(doc.page_count))
        finally:
            doc.close()

    def _extract_pdf_text_via_ocr(self, file_path: Path) -> str:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise RuntimeError(
                "rapidocr-onnxruntime is not available in this environment. "
                "Install system dependency libxcb1 or use a PDF with embedded text."
            ) from exc
        doc = fitz.open(file_path)
        engine = RapidOCR()
        page_texts: list[str] = []

        try:
            for i in range(doc.page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image_bytes = pix.tobytes("png")
                result = engine(image_bytes)
                items = result[0] if isinstance(result, tuple) else result
                page_texts.append("\n".join(item[1] for item in (items or [])))
        finally:
            doc.close()

        return "\n".join(page_texts)

    def _parse_transactions(self, content: str) -> list[RawTransaction]:
        lines = [self._normalize_line(line) for line in content.splitlines()]
        lines = [line for line in lines if line]

        first_row_idx = next((i for i, line in enumerate(lines) if DATE_RE.fullmatch(line)), None)
        if first_row_idx is None:
            logger.warning("CMB PDF parser: first transaction row not found")
            return []

        transactions: list[RawTransaction] = []
        i = first_row_idx
        while i < len(lines):
            line = lines[i]
            if self._is_page_marker(line):
                i = self._skip_page_non_data_lines(lines, i + 1)
                continue
            if not DATE_RE.fullmatch(line):
                i += 1
                continue
            tx, next_idx = self._parse_transaction_row(lines, i)
            if tx:
                transactions.append(tx)
            i = next_idx

        return transactions

    def _parse_transaction_row(self, lines: list[str], start_idx: int) -> tuple[RawTransaction | None, int]:
        if start_idx + 4 >= len(lines):
            return None, len(lines)

        date_str = lines[start_idx]
        currency = lines[start_idx + 1]
        amount_str = lines[start_idx + 2]
        balance_str = lines[start_idx + 3]
        summary = lines[start_idx + 4]

        if not AMOUNT_RE.fullmatch(amount_str) or not AMOUNT_RE.fullmatch(balance_str):
            logger.debug("CMB PDF parser: invalid amount row at %s", start_idx)
            return None, start_idx + 1

        counterparty_parts: list[str] = []
        idx = start_idx + 5
        while idx < len(lines):
            line = lines[idx]
            if DATE_RE.fullmatch(line) or self._is_page_marker(line) or self._is_page_boundary_noise(line):
                break
            if line not in HEADER_SKIP_LINES:
                counterparty_parts.append(line)
            idx += 1

        merchant = "".join(counterparty_parts)
        amount = float(amount_str.replace(",", ""))
        direction = self._direction_from_amount(amount)
        transaction_at = datetime.strptime(date_str, "%Y-%m-%d")
        external_id = f"cmb:{date_str}:{amount_str}:{balance_str}:{summary}:{merchant}"

        raw_data = {
            "记账日期": date_str,
            "货币": currency,
            "交易金额": amount_str,
            "联机余额": balance_str,
            "交易摘要": summary,
            "对手信息": merchant,
        }

        return RawTransaction(
            source=BillSource.CMB,
            direction=direction,
            amount=abs(amount),
            currency=currency,
            merchant=merchant,
            description=summary,
            transaction_at=transaction_at,
            raw_data=raw_data,
            external_id=external_id,
        ), idx

    def _direction_from_amount(self, amount: float) -> TransactionDirection:
        if amount < 0:
            return TransactionDirection.EXPENSE
        if amount > 0:
            return TransactionDirection.INCOME
        return TransactionDirection.TRANSFER

    def _is_page_marker(self, line: str) -> bool:
        return bool(re.fullmatch(r"\d+/\d+", line))

    def _skip_page_non_data_lines(self, lines: list[str], start_idx: int) -> int:
        idx = start_idx
        while idx < len(lines):
            line = lines[idx]
            if DATE_RE.fullmatch(line):
                return idx
            if line in HEADER_SKIP_LINES or self._is_page_boundary_noise(line) or not line:
                idx += 1
                continue
            if any(marker in line for marker in TRAILING_NOTE_MARKERS):
                idx += 1
                continue
            idx += 1
        return idx

    def _is_page_boundary_noise(self, line: str) -> bool:
        return bool(line) and not line.strip("—-")

    def _normalize_line(self, line: str) -> str:
        normalized = line.replace("\xa0", " ").strip()
        for marker in TRAILING_NOTE_MARKERS:
            marker_idx = normalized.find(marker)
            if marker_idx > 0:
                normalized = normalized[:marker_idx].rstrip("—- ")
                break
        return normalized


register(ChinaMerchantsBankPdfParser())
