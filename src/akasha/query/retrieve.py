"""Stage 5 — retrieve the most relevant chunks for a question."""

from __future__ import annotations

from ..config import TOP_K
from ..index.embed import embed_texts
from ..index.store import VectorStore
from ..types import Retrieved


def retrieve(question: str, k: int = TOP_K, store: VectorStore | None = None) -> list[Retrieved]:
    """Embed the question and return the top-k governance-filtered chunks.

    Pass an existing `store` to reuse a connection; otherwise one is opened and
    closed here.
    """
    query_vector = embed_texts([question])[0]
    own_store = store is None
    store = store or VectorStore()
    try:
        return store.query(query_vector, k=k)
    finally:
        if own_store:
            store.close()
