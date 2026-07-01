"""POST /api/v1/search — hybrid retrieval only, no generation."""

from fastapi import APIRouter

from ...query.retrieve import retrieve
from ..schemas import SearchHit, SearchRequest, SearchResponse

router = APIRouter(tags=["retrieval"])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    # sync def → FastAPI runs it in a threadpool, so the blocking embed + DB
    # calls don't stall the event loop.
    hits = retrieve(req.question, k=req.k)
    return SearchResponse(
        query=req.question,
        count=len(hits),
        hits=[
            SearchHit(
                chunk_id=h.chunk.id,
                source_title=h.chunk.source_title,
                page_start=h.chunk.page_start,
                page_end=h.chunk.page_end,
                section=h.chunk.section,
                score=round(h.score, 4),
                text=h.chunk.text,
            )
            for h in hits
        ],
    )
