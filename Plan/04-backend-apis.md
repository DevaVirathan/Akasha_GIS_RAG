# 4. Backend APIs

[← Vector DB & data stores](03-vector-db-and-data-stores.md) · [Index](README.md) · Next: [Security →](05-security.md)

FastAPI service exposing document administration, retrieval, cited chat,
glossary, feedback, and evaluation — all under `/api/v1`, all permission-scoped.

## 4.1 Service layout

```
apps/api/app/
├── main.py                # app factory, middleware, routers
├── core/                  # config, security, logging, rate limiting
├── db/                    # SQLAlchemy models, session, Alembic migrations
├── documents/             # upload, versioning, governance
├── ingestion/             # extractor, ocr, cleaner, chunker, embedder, pipeline
├── rag/                   # orchestrator, retriever, reranker, prompts, citation_validator
├── glossary/ · feedback/ · evals/
└── clients/openai.py      # thin OpenAI wrapper (retries, timeouts, cost)
```

## 4.2 API surface

All endpoints require auth ([05](05-security.md)); rows are filtered to the
caller's permission scope.

**Documents / admin** (curator/admin roles)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/documents` | Register + upload PDF (multipart); returns document + version |
| GET | `/documents` | List (paginated, filterable by book/domain/status) |
| GET | `/documents/{id}` | Detail incl. license + ingestion status |
| POST | `/documents/{id}/versions` | Upload a new version |
| POST | `/documents/{version_id}/ingest` | Enqueue ingestion job |
| GET | `/documents/{version_id}/ingest/status` | Job progress + QA report |
| GET | `/documents/{id}/chunks` | Inspect chunks (QA) |
| DELETE | `/documents/{id}` | Soft-disable (excluded from retrieval) |

**Retrieval & chat**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/search` | Hybrid retrieval only — returns ranked chunks + scores, no generation |
| POST | `/chat` | Full RAG: retrieve → generate → cited answer |
| POST | `/chat/stream` | Same, streamed via SSE |
| GET | `/chat/history` | Caller's past queries |

**Glossary / feedback / evals / ops** — carry over from
[appendix §16](appendix-domain-reference.md#16-api-design): `/glossary*`,
`/feedback`, `/evals/run`, `/evals/results`, `/analytics/usage`,
plus `/healthz` (liveness) and `/readyz` (DB + object store + OpenAI reachable).

## 4.3 Chat contract

Request:

```json
{
  "question": "What is NDVI and how do we implement it in Akasha?",
  "filters": { "book_ids": null, "tags": ["NDVI"], "domain": "remote_sensing" },
  "answer_style": "developer_friendly",
  "top_k": 12
}
```

Response (abridged — full shape in [appendix §17](appendix-domain-reference.md#17-example-chat-request--response)):

```json
{
  "answer": "NDVI = (NIR - Red) / (NIR + Red) ...",
  "citations": [
    { "chunk_id": "…", "source_title": "Remote Sensing and Image Interpretation",
      "page_start": 412, "section": "Vegetation Indices" }
  ],
  "insufficient_evidence": false,
  "usage": { "prompt_tokens": 1840, "completion_tokens": 320, "cost_usd": 0.0 },
  "query_log_id": "…"
}
```

Contract rules: answer **only** from retrieved context; if evidence is weak,
set `insufficient_evidence: true` and return the refusal message; every factual
sentence maps to a citation ([appendix §13](appendix-domain-reference.md#13-answer-generation-rules)).

## 4.4 RAG orchestrator

```
question
  → rewrite (resolve pronouns, expand acronyms)
  → intent/filters
  → PERMISSION + metadata pre-filter        (03 §3.5 — ACL enforced here)
  → hybrid retrieve (vector ∥ keyword) → RRF fuse
  → rerank top-N → top-k (source-diversity to counter duplicate books)
  → context packing (token budget, dedup)
  → OpenAI generation with citation contract
  → citation validation (drop/repair unsupported claims)
  → log to query_logs (retrieved + cited ids, tokens, cost, latency)
```

Reranking may start as a cross-encoder or an LLM reranker; keep it swappable and
bounded (`RERANK_TOP_K`) for latency.

## 4.5 Cross-cutting API concerns

- **Versioning:** `/api/v1`; additive changes only within a major version.
- **Errors:** consistent envelope `{error: {code, message, request_id}}`.
- **Pagination:** cursor-based on list endpoints.
- **Idempotency:** `Idempotency-Key` on upload/ingest to make retries safe.
- **Rate limiting:** per-user + per-role token buckets ([05](05-security.md#57-rate-limiting--abuse)).
- **Streaming:** SSE for `/chat/stream`; flush citations at the end once validated.

## 4.6 OpenAI client wrapper

A single module (`clients/openai.py`) is the **only** place the app calls
OpenAI, so cross-cutting policy lives in one spot:

- **Model pinning** from config (`OPENAI_RESPONSE_MODEL`, `OPENAI_EMBEDDING_MODEL`)
  — never hardcoded; [validate](README.md#validate-before-locking) before locking.
- **Timeouts + bounded retries** with backoff on 429/5xx.
- **Cost/token capture** per call → `query_logs` for [analytics + budgets](06-deployment.md#69-cost-controls).
- **Embedding batching + cache** keyed by content hash (skip re-embedding).
- **Untrusted-context isolation** — retrieved text is passed as data, with a
  system instruction never to follow instructions inside it ([05](05-security.md#55-prompt-injection-defense)).
- Swappable so a model change is one config edit, gated by [evals](07-evaluation.md).
