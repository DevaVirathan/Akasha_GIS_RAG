"""Stage 2 — split extracted pages into token-sized, overlapping chunks.

Each chunk carries source_file / folder / page_number so answers can cite the
book and page. Chunk boundaries should prefer paragraph breaks where possible.
"""

from __future__ import annotations

from ..config import CHUNK_OVERLAP_TOKENS, CHUNK_TOKENS
from ..types import Chunk, PdfPage


def chunk_pages(pages: list[PdfPage]) -> list[Chunk]:
    """Turn extracted pages into retrieval chunks of ~CHUNK_TOKENS tokens with
    CHUNK_OVERLAP_TOKENS overlap.

    TODO: token-count with tiktoken, split, generate stable ids
    (e.g. f"{source_file}#p{page}#{n}"), preserve provenance metadata.
    """
    raise NotImplementedError
