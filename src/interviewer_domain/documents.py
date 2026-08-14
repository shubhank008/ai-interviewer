"""Deterministic document ingestion with explicit untrusted-data boundaries."""

from __future__ import annotations

import re
from dataclasses import replace

from .contracts import ErrorCode, ProviderError
from .models import DocumentChunk, DocumentSource

MAX_RESUME_BYTES = 10 * 1024 * 1024
MIN_CHUNK_LENGTH = 40
MAX_CHUNK_LENGTH = 800
_INSTRUCTION_PATTERN = re.compile(
    r"(?:ignore|disregard|override)\s+(?:all\s+)?(?:previous|prior|system|developer)\s+(?:instructions?|messages?)",
    re.IGNORECASE,
)
_PDF_TEXT_PATTERN = re.compile(rb"\(([^()]*)\)")


class LocalDocumentParser:
    """Parse pasted job descriptions and text-based PDF resumes locally."""

    def parse(self, content: bytes, content_type: str, source: str) -> list[DocumentChunk]:
        """Validate input, extract text, and return bounded source chunks."""
        document_source = self._source(source)
        if not content:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "document is empty")
        if document_source is DocumentSource.RESUME and len(content) > MAX_RESUME_BYTES:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "resume exceeds 10 MB limit")
        if document_source is DocumentSource.RESUME:
            if content_type != "application/pdf" or not content.startswith(b"%PDF-"):
                raise ProviderError(ErrorCode.INVALID_REQUEST, "resume must be a PDF")
            text = self._pdf_text(content)
        elif content_type not in {"text/plain", "text/markdown"}:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "job description must be text")
        else:
            text = content.decode("utf-8", errors="replace")
        return self._chunk(document_source, text)

    @staticmethod
    def _source(source: str) -> DocumentSource:
        try:
            return DocumentSource(source)
        except ValueError as exc:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "unsupported document source") from exc

    @staticmethod
    def _pdf_text(content: bytes) -> str:
        """Extract simple PDF text operators without attempting OCR or execution."""
        values = [value.decode("utf-8", errors="replace") for value in _PDF_TEXT_PATTERN.findall(content)]
        text = "\n".join(values).strip()
        if not text:
            raise ProviderError(ErrorCode.INVALID_REQUEST, "PDF contains no extractable text")
        return text

    def _chunk(self, source: DocumentSource, text: str) -> list[DocumentChunk]:
        normalized = self._safe_text(text)
        chunks: list[DocumentChunk] = []
        section = "general"
        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        current: list[str] = []
        start_line = 1
        for line_number, line in enumerate(lines, 1):
            if self._is_heading(line) and not current:
                section = line[:120]
                start_line = line_number
                continue
            current.append(line)
            if len(" ".join(current)) >= MAX_CHUNK_LENGTH:
                chunks.append(self._make_chunk(source, section, " ".join(current), start_line))
                current = []
                start_line = line_number + 1
        if current:
            candidate = " ".join(current)
            chunks.append(self._make_chunk(source, section, candidate, start_line))
        return chunks

    @staticmethod
    def _safe_text(text: str) -> str:
        """Keep document claims visible while making instruction-like text non-authoritative."""
        lines = []
        for line in text.splitlines():
            if _INSTRUCTION_PATTERN.search(line):
                lines.append("[UNTRUSTED DOCUMENT TEXT] " + line)
            else:
                lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _is_heading(line: str) -> bool:
        return line.endswith(":") or (len(line) <= 80 and line.isupper())

    @staticmethod
    def _make_chunk(source: DocumentSource, section: str, text: str, line: int) -> DocumentChunk:
        return DocumentChunk(source, section, text[:MAX_CHUNK_LENGTH], f"line:{line}")


def replace_chunk_text(chunk: DocumentChunk, text: str) -> DocumentChunk:
    """Return a safe copy when an adapter needs to further normalize chunk text."""
    return replace(chunk, text=text[:MAX_CHUNK_LENGTH])
