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
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    insufficient_evidence: bool


class DocumentOut(BaseModel):
    document_id: str
    version_id: str
    version_no: int
    title: str
    status: str


class IngestAccepted(BaseModel):
    version_id: str
    status: str


class IngestStatusOut(BaseModel):
    version_id: str
    status: str
    chunks: int


class DocumentSummary(BaseModel):
    id: str
    title: str
    is_active: bool
    allowed_for_rag: bool
    status: str | None


class DevLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    is_admin: bool


class MeResponse(BaseModel):
    user_id: str
    email: str
    is_admin: bool
