"""Stage 3 — embed text with OpenAI.

Batched to respect request limits. `dimensions` is pinned to EMBED_DIM so the
vectors always match the VECTOR(n) column (pgvector's ANN index caps at 2000;
text-embedding-3-* support shortening via this param). openai is imported lazily
so importing this module doesn't require the package.
"""

from __future__ import annotations

from ..config import EMBED_DIM, EMBED_MODEL, require

_BATCH_SIZE = 128


def embed_texts(
    texts: list[str],
    *,
    model: str = EMBED_MODEL,
    dimensions: int = EMBED_DIM,
    batch_size: int = _BATCH_SIZE,
) -> list[list[float]]:
    """Return one embedding vector per input text using the OpenAI API."""
    if not texts:
        return []

    from openai import OpenAI

    client = OpenAI(api_key=require("OPENAI_API_KEY"))
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        resp = client.embeddings.create(model=model, input=batch, dimensions=dimensions)
        vectors.extend(item.embedding for item in resp.data)
    return vectors
