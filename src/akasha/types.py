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
    """A retrieval unit persisted in the `chunks` table (Plan/03, migration 0001).

    Required fields identify the row; the rest are optional metadata. `id` is
    assigned by the DB (gen_random_uuid) when None. `source_title` is not stored
    on the chunk — it is populated from documents.title on retrieval.
    """

    document_id: str
    document_version_id: str
    chunk_index: int
    text: str
    id: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    chapter: str | None = None
    section: str | None = None
    heading_path: str | None = None
    token_count: int | None = None
    domain: str | None = None
    difficulty: str | None = None
    tags: list[str] = field(default_factory=list)
    is_ocr: bool = False
    source_title: str | None = None  # filled on retrieval only


@dataclass
class Retrieved:
    """A chunk returned by a similarity query, with its score (cosine similarity)."""

    chunk: Chunk
    score: float
