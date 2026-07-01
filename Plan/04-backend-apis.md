# 4. Backend APIs

[← Vector DB & data stores](03-vector-db-and-data-stores.md) · [Index](README.md) · Next: [Security →](05-security.md)

FastAPI service exposing document administration, retrieval, and **streaming
cited chat**, plus glossary, feedback, and evaluation — all under `/api/v1`, all
requiring an authenticated `@thaarei.com` user ([05](05-security.md)). The design
is **schema-first** (OpenAPI is generated from Pydantic models), **resource-
oriented**, and **streaming-first for chat**: answers stream token-by-token over
SSE, so the user feels *time-to-first-token*, not full-answer latency.

## 4.1 Service layout

```
apps/api/app/
├── main.py                # app factory; middleware: auth, request-id, rate-limit, CORS, GZip
├── core/                  # config, security, Problem-Details errors, logging, rate limiting
├── db/                    # SQLAlchemy models, session, Alembic migrations
├── schemas/               # Pydantic request/response models — the OpenAPI source of truth
├── documents/             # upload, versioning, governance
├── ingestion/             # extractor, ocr, cleaner, chunker, embedder, pipeline
├── rag/                   # orchestrator, retriever, reranker, prompts, citation_validator
├── chat/                  # conversations, messages, SSE stream writer
├── glossary/ · feedback/ · evals/
└── clients/openai.py      # thin OpenAI wrapper (streaming, retries, timeouts, cost, cancel)
```

## 4.2 API surface

All endpoints require an authenticated `@thaarei.com` user. There is no role
hierarchy: every employee has equal read access to the approved corpus, so
responses are **not** per-user row-filtered. Admin endpoints additionally
require the `is_admin` flag.

Chat is modelled as **messages inside a conversation** (mirrors the
`conversations` / `query_logs` tables in [03 §3.4](03-vector-db-and-data-stores.md#34-schema))
rather than a bare `/chat` verb — this gives durable history, feedback anchored
to a specific answer, and a clean place to stream from.

**Conversations & chat** (any employee)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/conversations` | Start a conversation (optional first message) → `201` |
| GET | `/conversations` | List caller's conversations (cursor-paginated) |
| GET | `/conversations/{id}` | Conversation with its messages |
| POST | `/conversations/{id}/messages` | Ask a question. **Streams SSE** when `Accept: text/event-stream`; otherwise returns the completed assistant message (`200`). |
| DELETE | `/conversations/{id}` | Delete caller's conversation → `204` |
| POST | `/messages/{id}/feedback` | Thumbs up/down + note on a specific assistant message |

Streaming is negotiated by the **`Accept` header on one canonical endpoint**,
not a parallel `/chat/stream` path — the resource is the same, only the
representation differs (`text/event-stream` vs `application/json`). A
`?stream=true` query param is the fallback if an intermediary strips `Accept`.

**Retrieval (stateless)**

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/search` | Hybrid retrieval only — ranked chunks + scores, no generation |

**Documents / admin** (`is_admin` only)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/documents` | Register + upload PDF (multipart); `Idempotency-Key` honoured → `201` |
| GET | `/documents` | List (cursor-paginated; filter by book/domain/status) |
| GET | `/documents/{id}` | Detail incl. license + ingestion status (returns `ETag`) |
| POST | `/documents/{id}/versions` | Upload a new version (`If-Match` on the doc's `ETag`) |
| POST | `/documents/{version_id}/ingest` | Enqueue ingestion → `202 Accepted` + `Location: …/ingest/status` |
| GET | `/documents/{version_id}/ingest/status` | Job progress + QA report |
| GET | `/documents/{id}/chunks` | Inspect chunks (QA) |
| DELETE | `/documents/{id}` | Soft-disable (excluded from retrieval) → `204` |

**Glossary / evals / ops** — `/glossary*`, `/evals/run`, `/evals/results`,
`/analytics/usage` ([appendix §16](appendix-domain-reference.md#16-api-design)),
plus `/healthz` (liveness), `/readyz` (DB + object store + OpenAI reachable), and
`/metrics` (Prometheus).

## 4.3 Chat contract (non-streaming form)

Request — `POST /conversations/{id}/messages`:

```json
{
  "question": "What is NDVI and how do we implement it in Akasha?",
  "filters": { "book_ids": null, "tags": ["NDVI"], "domain": "remote_sensing" },
  "answer_style": "developer_friendly",
  "top_k": 12
}
```

Response — `200` (buffered; identical fields are delivered as SSE events when
streaming, see [§4.7](#47-streaming-responses-sse)):

```json
{
  "message_id": "…",
  "conversation_id": "…",
  "answer": "NDVI = (NIR - Red) / (NIR + Red) … [S1]",
  "citations": [
    { "marker": "S1", "chunk_id": "…", "source_title": "Remote Sensing and Image Interpretation",
      "page_start": 412, "section": "Vegetation Indices" }
  ],
  "insufficient_evidence": false,
  "usage": { "prompt_tokens": 1840, "completion_tokens": 320, "cost_usd": 0.0 },
  "query_log_id": "…"
}
```

Contract rules: answer **only** from retrieved context; emit inline citation
markers (`[S1]`, `[S2]`) that map to the `citations` array; if evidence is weak,
set `insufficient_evidence: true` and return the refusal message; every factual
sentence carries a marker ([appendix §13](appendix-domain-reference.md#13-answer-generation-rules)).

## 4.4 RAG orchestrator

```
question
  → rewrite (resolve pronouns, expand acronyms)
  → intent/filters
  → GOVERNANCE + metadata pre-filter     (03 §3.7 — published/approved gate, no ACL)
  → hybrid retrieve (vector ∥ keyword) → RRF fuse
  → rerank top-N → top-k (source-diversity to counter duplicate books)
  → context packing (token budget, dedup)
  → OpenAI generation with citation contract   ← streamed token-by-token (§4.7)
  → citation validation (drop/repair unsupported claims)
  → persist assistant message + log to query_logs (retrieved + cited ids, tokens, cost, TTFT, latency)
```

In streaming mode the generation step forwards each token as an SSE `delta`
while the full text is buffered so citation validation can run once generation
finishes. Reranking may start as a cross-encoder or an LLM reranker; keep it
swappable and bounded (`RERANK_TOP_K`) for latency.

## 4.5 Cross-cutting API concerns & standards

- **Versioning:** URI `/api/v1`; breaking changes ship as `/v2` and are
  pre-announced with `Deprecation` + `Sunset` response headers.
- **Errors:** RFC 9457 **Problem Details** (`application/problem+json`), never a
  bespoke shape:
  ```json
  { "type": "https://api.akasha/errors/validation",
    "title": "Invalid request", "status": 422,
    "detail": "top_k must be between 1 and 50",
    "instance": "/api/v1/conversations/…/messages",
    "request_id": "req_01H…" }
  ```
- **Status codes:** `200` read · `201` create · `202` async ingest (+`Location`)
  · `204` delete · `400` malformed · `401` missing/invalid token · `403` not
  `@thaarei.com` / not admin · `404` · `409` idempotency/version conflict ·
  `412` `If-Match` failed · `422` validation · `429` rate limit · `5xx`.
- **Pagination:** cursor-based; envelope `{ "data": […], "page": { "next_cursor": "…", "has_more": true } }`. No `OFFSET` scans.
- **Idempotency:** `Idempotency-Key` on POST create/upload/ingest; the server
  persists the first result and replays it for duplicate keys.
- **Concurrency:** `ETag` + `If-Match` optimistic locking on document mutations.
- **Rate limiting:** `RateLimit-Limit/Remaining/Reset` on every response,
  `Retry-After` on `429` ([05 §5.7](05-security.md#57-rate-limiting--abuse)).
- **Tracing:** accept W3C `traceparent`; return `X-Request-Id` on every response
  and echo it in Problem Details for support.
- **Contract-first:** OpenAPI served at `/openapi.json`; typed frontend clients
  are generated from it, not hand-written.

## 4.6 OpenAI client wrapper

A single module (`clients/openai.py`) is the **only** place the app calls
OpenAI, so cross-cutting policy lives in one spot:

- **Model pinning** from config (`OPENAI_RESPONSE_MODEL`, `OPENAI_EMBEDDING_MODEL`)
  — never hardcoded; [validate](README.md#validate-before-locking) before locking.
- **Streaming** — generation runs with `stream=True`; the wrapper yields token
  deltas to the SSE writer ([§4.7](#47-streaming-responses-sse)) and captures the
  final `usage` block. Retries apply **only before the first token** — once bytes
  are streamed a transparent retry would duplicate output, so mid-stream failures
  surface as a stream `error` event.
- **Cancellation** — a client disconnect is propagated to abort the upstream
  request so token billing stops immediately.
- **Timeouts + bounded retries** with backoff on `429`/`5xx` (connect + TTFT).
- **Cost/token capture** per call → `query_logs` for [analytics + budgets](06-deployment.md#69-cost-controls).
- **Embedding batching + cache** keyed by content hash (skip re-embedding).
- **Untrusted-context isolation** — retrieved text is passed as data, with a
  system instruction never to follow instructions inside it ([05](05-security.md#55-prompt-injection-defense)).
- Swappable so a model change is one config edit, gated by [evals](07-evaluation.md).

## 4.7 Streaming responses (SSE)

Chat streams over **Server-Sent Events**. SSE (not WebSocket) is the right fit:
the flow is unidirectional server→client, it rides plain HTTP/2 (proxy- and
load-balancer-friendly), and it has built-in reconnect semantics. Use WebSocket
only if we later need mid-generation client interrupts or bidirectional multiplex.

### Response headers

```
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no          # disable proxy (nginx) buffering so tokens flush live
```

### Event protocol

Named events with JSON payloads; the server flushes after each. Ordering is
`start → delta* → citations → usage → done` (or a terminal `error`):

```text
event: start
data: {"message_id":"m_01H…","conversation_id":"c_…","model":"<OPENAI_RESPONSE_MODEL>"}

event: delta
data: {"text":"NDVI is "}

event: delta
data: {"text":"a vegetation index computed from NIR and Red… [S1]"}

: keep-alive                       ← SSE comment heartbeat (~every 15s)

event: citations
data: {"citations":[{"marker":"S1","chunk_id":"…","source_title":"Remote Sensing and Image Interpretation","page_start":412,"section":"Vegetation Indices"}]}

event: usage
data: {"prompt_tokens":1840,"completion_tokens":320,"cost_usd":0.0,"ttft_ms":380}

event: done
data: {"finish_reason":"stop","insufficient_evidence":false,"query_log_id":"…"}
```

Mid-stream failure (after `200` + headers are already sent, so the HTTP status
can no longer change):

```text
event: error
data: {"type":"upstream_timeout","title":"Generation failed","request_id":"req_…"}
```

### Design decisions

- **Live tokens, citations last.** Citation validation needs the full answer, so
  `delta` events stream immediately for low TTFT, while the answer is buffered;
  the validated `citations` event is emitted at the end. The model writes inline
  `[S1]` markers as it goes, so streamed text already references sources that the
  final `citations` payload resolves — no rewrite of already-sent tokens.
- **Heartbeats.** A `: keep-alive` comment every ~15s defeats idle-timeout kills
  in proxies/load balancers without polluting the event stream.
- **Cancellation = cost control.** On client disconnect (`await request.is_disconnected()`
  in Starlette) the handler aborts the OpenAI stream ([§4.6](#46-openai-client-wrapper))
  so no further tokens are generated or billed.
- **Persistence.** On `done`, the assistant message + `query_logs` row are
  persisted (answer, citations, tokens, cost, TTFT, total latency). Feedback
  targets `message_id`.
- **Reconnect, not resume.** SSE `id:` / `Last-Event-ID` exist, but resuming a
  non-deterministic LLM stream mid-flight is impractical; on reconnect the client
  re-fetches the persisted message via `GET /conversations/{id}` instead. Persist
  incrementally so a dropped connection never loses a completed answer.
- **Pre-stream errors stay HTTP.** Auth, validation, rate-limit, and empty-
  retrieval failures happen *before* the first byte and return normal
  Problem-Details responses ([§4.5](#45-cross-cutting-api-concerns--standards));
  only post-first-token failures use the `error` event.
- **Client note.** The browser `EventSource` API cannot send an `Authorization`
  header or use `POST`; the frontend consumes the stream with `fetch()` +
  `ReadableStream` (Bearer JWT in the header), which also gives clean abort via
  `AbortController`.

### Observability

Track **TTFT**, tokens/sec, total stream duration, and disconnect/cancel rate
([06 §6.7](06-deployment.md#67-observability)) — TTFT is the number users
actually feel and the primary chat SLO.
