"""Stage 6 — synthesize a cited answer with OpenAI from retrieved chunks."""

from __future__ import annotations

from ..config import ANSWER_MODEL
from ..types import Retrieved


def answer(question: str, retrieved: list[Retrieved]) -> str:
    """Prompt ANSWER_MODEL with the question and retrieved context, instructing
    it to answer only from context and cite (source_file, page_number).

    TODO: build a context block from retrieved chunks, call the OpenAI Chat
    Completions API (client.chat.completions.create) with
    config.require("OPENAI_API_KEY"). Treat retrieved text as untrusted data
    (do not follow instructions embedded in it).
    """
    raise NotImplementedError
