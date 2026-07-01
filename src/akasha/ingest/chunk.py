"""Stage 2 — split extracted pages into token-sized chunks with provenance.

Each chunk carries document/version ids and its page number so answers can cite
the book and page. Chunking is per-page (exact page provenance); long pages are
split into overlapping token windows. Uses tiktoken when available, with a
word-count fallback so ingestion works even without it.
"""

from __future__ import annotations

from ..config import CHUNK_OVERLAP_TOKENS, CHUNK_TOKENS
from ..types import Chunk, PdfPage


def chunk_pages(
    pages: list[PdfPage],
    document_id: str,
    document_version_id: str,
    *,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap_tokens: int = CHUNK_OVERLAP_TOKENS,
) -> list[Chunk]:
    """Turn extracted pages into retrieval chunks with source metadata."""
    chunks: list[Chunk] = []
    index = 0
    for page in pages:
        text = page.text.strip()
        if not text:
            continue
        for piece in _split(text, chunk_tokens, overlap_tokens):
            chunks.append(
                Chunk(
                    document_id=document_id,
                    document_version_id=document_version_id,
                    chunk_index=index,
                    text=piece,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    is_ocr=page.is_ocr,
                    token_count=_count(piece),
                )
            )
            index += 1
    return chunks


_ENCODER = None


def _encoder():
    global _ENCODER
    if _ENCODER is None:
        import tiktoken

        _ENCODER = tiktoken.get_encoding("cl100k_base")
    return _ENCODER


def _split(text: str, size: int, overlap: int) -> list[str]:
    try:
        enc = _encoder()
        tokens = enc.encode(text)
        if len(tokens) <= size:
            return [text]
        step = max(1, size - overlap)
        out: list[str] = []
        for start in range(0, len(tokens), step):
            window = tokens[start : start + size]
            if not window:
                break
            out.append(enc.decode(window).strip())
            if start + size >= len(tokens):
                break
        return out
    except Exception:
        return _split_words(text, size, overlap)


def _split_words(text: str, size: int, overlap: int) -> list[str]:
    """Fallback: ~0.75 words/token approximation when tiktoken is unavailable."""
    words = text.split()
    wsize = max(1, int(size * 0.75))
    wover = int(overlap * 0.75)
    if len(words) <= wsize:
        return [text]
    step = max(1, wsize - wover)
    out: list[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + wsize]
        if not window:
            break
        out.append(" ".join(window))
        if start + wsize >= len(words):
            break
    return out


def _count(text: str) -> int | None:
    try:
        return len(_encoder().encode(text))
    except Exception:
        return None
