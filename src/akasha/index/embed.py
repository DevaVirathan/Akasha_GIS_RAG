"""Stage 3 — embed text with OpenAI.

Batch requests to respect rate/size limits; the corpus is large, so cache
embeddings and make this resumable.
"""

from __future__ import annotations

from ..config import EMBED_MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return one embedding vector per input text using EMBED_MODEL.

    TODO: construct openai.OpenAI(api_key=config.require("OPENAI_API_KEY")),
    call client.embeddings.create(model=EMBED_MODEL, input=batch), and return
    [d.embedding for d in resp.data]. Batch inputs to stay within request limits.
    """
    raise NotImplementedError
