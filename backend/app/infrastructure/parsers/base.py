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
            return any(self.can_parse(content) for content in self._read_text_candidates(file_path))
        except Exception:
            return False

    @abstractmethod
    def parse(self, content: str) -> list[RawTransaction]:
        """Parse text content into RawTransaction list."""

    def parse_file(self, file_path: Path) -> list[RawTransaction]:
        """Parse a file into RawTransaction list."""
        candidates = self._read_text_candidates(file_path)
        for content in candidates:
            if self.can_parse(content):
                return self.parse(content)
        return self.parse(candidates[0])

    def _read_text_file(self, file_path: Path) -> str:
        return self._read_text_candidates(file_path)[0]

    def _read_text_candidates(self, file_path: Path) -> list[str]:
        raw = file_path.read_bytes()
        detected = chardet.detect(raw)
        encodings: list[str] = []

        detected_encoding = detected.get("encoding")
        if detected_encoding:
            encodings.append(detected_encoding)

        encodings.extend(["utf-8-sig", "utf-8", "gb18030", "gbk", "utf-16"])

        candidates: list[str] = []
        seen: set[str] = set()
        for encoding in encodings:
            normalized = encoding.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            try:
                candidates.append(raw.decode(encoding))
            except Exception:
                continue

        if not candidates:
            candidates.append(raw.decode("utf-8", errors="replace"))

        return candidates
