"""POST /api/v1/chat — retrieve → generate. SSE stream or buffered JSON.

Streaming (Accept: text/event-stream) emits named events:
    start → delta* → citations → usage → done
Buffered (any other Accept) returns a ChatResponse.

TODO (auth/hardening pass, Plan/04 §4.7): heartbeats + client-disconnect
cancellation to stop token billing on abort.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ...config import ANSWER_MODEL
from ...query.answer import REFUSAL, answer, answer_stream
from ...query.retrieve import retrieve
from ...types import Retrieved
from ..schemas import ChatRequest, ChatResponse, Citation

router = APIRouter(tags=["chat"])


def _citations(retrieved: list[Retrieved]) -> list[Citation]:
    return [
        Citation(
            marker=f"S{i}",
            chunk_id=r.chunk.id,
            source_title=r.chunk.source_title,
            page_start=r.chunk.page_start,
            section=r.chunk.section,
            score=round(r.score, 4),
        )
        for i, r in enumerate(retrieved, start=1)
    ]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _stream(question: str, k: int) -> Iterator[str]:
    retrieved = retrieve(question, k=k)
    yield _sse("start", {"model": ANSWER_MODEL, "retrieved": len(retrieved)})

    stats: dict = {}
    started = time.perf_counter()
    ttft_ms: int | None = None
    parts: list[str] = []
    for delta in answer_stream(question, retrieved, stats=stats):
        if ttft_ms is None:
            ttft_ms = int((time.perf_counter() - started) * 1000)
        parts.append(delta)
        yield _sse("delta", {"text": delta})

    yield _sse("citations", {"citations": [c.model_dump() for c in _citations(retrieved)]})
    yield _sse(
        "usage",
        {
            "prompt_tokens": stats.get("prompt_tokens"),
            "completion_tokens": stats.get("completion_tokens"),
            "ttft_ms": ttft_ms,
        },
    )
    full = "".join(parts).strip()
    yield _sse("done", {"finish_reason": "stop", "insufficient_evidence": full == REFUSAL})


@router.post("/chat")
def chat(req: ChatRequest, request: Request):
    if "text/event-stream" in request.headers.get("accept", ""):
        return StreamingResponse(
            _stream(req.question, req.k),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    # Buffered representation.
    retrieved = retrieve(req.question, k=req.k)
    text = answer(req.question, retrieved)
    return ChatResponse(
        answer=text,
        citations=_citations(retrieved),
        insufficient_evidence=text.strip() == REFUSAL,
    )
