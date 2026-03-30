from abc import ABC, abstractmethod
from pathlib import Path

import chardet

from app.domain.transaction.models import RawTransaction


class BillParserAdapter(ABC):
    @property
    @abstractmethod
    def source_type(self) -> str:
        """Unique identifier, e.g. 'wechat', 'alipay'"""

    @abstractmethod
    def can_parse(self, content: str) -> bool:
        """Auto-detect whether this parser handles the given text content."""

    def can_parse_file(self, file_path: Path) -> bool:
        """Auto-detect whether this parser handles the given file."""
        try:
            return self.can_parse(self._read_text_file(file_path))
        except Exception:
            return False

    @abstractmethod
    def parse(self, content: str) -> list[RawTransaction]:
        """Parse text content into RawTransaction list."""

    def parse_file(self, file_path: Path) -> list[RawTransaction]:
        """Parse a file into RawTransaction list."""
        return self.parse(self._read_text_file(file_path))

    def _read_text_file(self, file_path: Path) -> str:
        raw = file_path.read_bytes()
        detected = chardet.detect(raw)
        encoding = detected.get("encoding") or "utf-8"
        return raw.decode(encoding, errors="replace")
