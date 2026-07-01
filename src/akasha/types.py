"""Shared data structures passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PdfPage:
    """One extracted page, with provenance for citations."""

    source_file: str  # e.g. "Basudev Bhatta_Remote Sensing and GIS_Second edition.pdf"
    folder: str       # "Bsc Agri" | "BTech Agri"
    page_number: int  # 1-indexed
    text: str
    is_ocr: bool = False  # True if produced by the OCR fallback


@dataclass
class Chunk:
    """A retrieval unit derived from one or more pages."""

    id: str
    text: str
    source_file: str
    folder: str
    page_number: int
    metadata: dict = field(default_factory=dict)


@dataclass
class Retrieved:
    """A chunk returned by a similarity query, with its score."""

    chunk: Chunk
    score: float
