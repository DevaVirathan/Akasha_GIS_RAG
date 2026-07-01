"""Stage 5 — retrieve the most relevant chunks for a question."""

from __future__ import annotations

from ..config import TOP_K
from ..types import Retrieved


def retrieve(question: str, k: int = TOP_K) -> list[Retrieved]:
    """Embed the question (input_type="query") and return the top-k chunks.

    TODO: embed via index.embed.embed_texts, query index.store.VectorStore.
    Consider de-duplicating near-identical chunks from the overlapping corpus.
    """
    raise NotImplementedError
