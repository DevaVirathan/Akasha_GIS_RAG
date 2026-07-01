"""Stage 4 — persist chunks + embeddings in a local vector store (Chroma).

The store lives under config.STORAGE_DIR and is gitignored. Metadata
(source_file, folder, page_number) is stored alongside each vector for citations.
"""

from __future__ import annotations

from ..config import STORAGE_DIR
from ..types import Chunk, Retrieved


class VectorStore:
    """Thin wrapper over a persistent Chroma collection."""

    def __init__(self, path=STORAGE_DIR, collection: str = "textbooks") -> None:
        # TODO: chromadb.PersistentClient(path=str(path)).get_or_create_collection(...)
        self.path = path
        self.collection = collection

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Upsert chunks and their vectors (ids from Chunk.id for idempotency)."""
        raise NotImplementedError

    def query(self, embedding: list[float], k: int) -> list[Retrieved]:
        """Return the top-k most similar chunks with scores."""
        raise NotImplementedError
