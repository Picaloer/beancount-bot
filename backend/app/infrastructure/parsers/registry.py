"""
Parser registry — new parsers self-register via register().
Auto-detection tries each registered parser in order.
"""
from pathlib import Path

from app.core.exceptions import UnsupportedFormatError
from app.domain.transaction.models import RawTransaction
from app.infrastructure.parsers.base import BillParserAdapter

_parsers: dict[str, BillParserAdapter] = {}


def register(parser: BillParserAdapter) -> None:
    _parsers[parser.source_type] = parser


def get_parser(source_type: str) -> BillParserAdapter:
    if source_type not in _parsers:
        raise UnsupportedFormatError(f"No parser registered for source type: {source_type}")
    return _parsers[source_type]


def auto_detect(content: str) -> BillParserAdapter:
    for parser in _parsers.values():
        if parser.can_parse(content):
            return parser
    raise UnsupportedFormatError(
        "Cannot identify bill format. Supported: WeChat Pay, Alipay, China Merchants Bank PDF."
    )


def auto_detect_file(file_path: str | Path) -> BillParserAdapter:
    path = Path(file_path)
    for parser in _parsers.values():
        if parser.can_parse_file(path):
            return parser
    raise UnsupportedFormatError(
        "Cannot identify bill format. Supported: WeChat Pay, Alipay, China Merchants Bank PDF."
    )


def parse(content: str) -> tuple[str, list[RawTransaction]]:
    """Auto-detect parser and return (source_type, transactions)."""
    parser = auto_detect(content)
    return parser.source_type, parser.parse(content)


def parse_file(file_path: str | Path) -> tuple[str, list[RawTransaction]]:
    """Auto-detect parser from a file and return (source_type, transactions)."""
    parser = auto_detect_file(file_path)
    return parser.source_type, parser.parse_file(Path(file_path))
