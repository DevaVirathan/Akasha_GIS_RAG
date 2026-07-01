"""Pydantic request/response models — the OpenAPI source of truth."""

from pydantic import BaseModel, Field

from ..config import TOP_K


class SearchRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=TOP_K, ge=1, le=50)


class SearchHit(BaseModel):
    chunk_id: str | None
    source_title: str | None
    page_start: int | None
    page_end: int | None
    section: str | None
    score: float
    text: str


class SearchResponse(BaseModel):
    query: str
    count: int
    hits: list[SearchHit]


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=TOP_K, ge=1, le=50)


class Citation(BaseModel):
    marker: str
    chunk_id: str | None
    source_title: str | None
    page_start: int | None
    section: str | None
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    insufficient_evidence: bool
