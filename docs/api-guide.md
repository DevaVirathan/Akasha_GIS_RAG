# Akasha RAG — API Guide (manual testing)

A practical reference for exercising the API by hand, e.g. in Swagger UI at
**http://127.0.0.1:8000/docs**. Covers every endpoint, its payload, and the
end-to-end flows.

---

## 1. Run it locally

```powershell
# 1) data services (Postgres+pgvector, Redis, MinIO)
docker compose up -d

# 2) schema
python -m alembic upgrade head

# 3) API server  (needs OPENAI_API_KEY in .env)
$env:PYTHONPATH="src"; python -m uvicorn akasha.api.main:app --port 8000

# 4) ingestion worker (separate terminal) — only needed to run ingest jobs
$env:PYTHONPATH="src"; python scripts/run_worker.py
```

- Swagger UI: http://127.0.0.1:8000/docs · ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

---

## 2. Authentication (`@thaarei.com` only)

Every `/api/v1/*` endpoint needs a **Bearer JWT** whose `email` ends in
`@thaarei.com`. `/healthz`, `/readyz`, and the docs are open.

- **Identity** comes from the token; **authorization** (`is_admin`, `is_active`)
  comes from the DB, which is upserted just-in-time on first call.
- **Get a token via the API** — `POST /api/v1/auth/dev-login` (enabled when `DEV_AUTH=true`):
  ```bash
  curl -X POST http://127.0.0.1:8000/api/v1/auth/dev-login \
    -H "Content-Type: application/json" -d '{"email":"devavirathan@thaarei.com"}'
  # -> {"access_token":"<jwt>","token_type":"bearer","email":"…","is_admin":true}
  ```
  Confirm identity anytime with `GET /api/v1/me`.
- **Or mint a token via CLI** (HS256, 24h):
  ```powershell
  $env:PYTHONPATH="src"; python scripts/dev_token.py devavirathan@thaarei.com
  # admin claim (admin still requires is_admin=true in the DB):
  $env:PYTHONPATH="src"; python scripts/dev_token.py someone@thaarei.com --admin
  ```
- **Grant admin** (needed for the `documents` endpoints):
  ```sql
  UPDATE users SET is_admin = true WHERE email = 'devavirathan@thaarei.com';
  ```

### Authorize in Swagger

1. Open **/docs** → click **Authorize** 🔒 (top-right).
2. Paste the token value (just the JWT, no `Bearer` prefix).
3. Authorize → Close. All "Try it out" calls now send the header.

Header sent on every request:
```
Authorization: Bearer <token>
```

---

## 3. Conventions

- **Base URL:** `http://127.0.0.1:8000`, API under `/api/v1`.
- **Errors:** RFC 9457 Problem Details (`application/problem+json`):
  ```json
  { "type": "https://api.akasha/errors/validation", "title": "Invalid request",
    "status": 422, "detail": "…", "instance": "/api/v1/search",
    "request_id": "…" }
  ```
- **Status codes:** `200` ok · `201` created · `202` accepted (async) · `400`
  bad request · `401` missing/invalid token · `403` not `@thaarei.com` / not
  admin · `404` not found · `422` validation · `500` server error.
- **Every response** carries an `X-Request-Id` header (echo it when reporting bugs).

---

## 4. Endpoints

### 4.1 Health (open)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/healthz` | Liveness |
| GET | `/readyz` | Readiness (checks DB) |

```bash
curl http://127.0.0.1:8000/healthz
# {"status":"ok"}
curl http://127.0.0.1:8000/readyz
# {"status":"ready","checks":{"database":true}}   (503 if DB down)
```

### 4.2 `POST /api/v1/search` — retrieval only (auth)

Returns ranked chunks; **no answer generation**.

**Request**
```json
{ "question": "What is NDVI?", "k": 3 }
```
| Field | Type | Rules |
|-------|------|-------|
| `question` | string | 1–2000 chars |
| `k` | int | 1–50, default 6 |

**Response `200`**
```json
{
  "query": "What is NDVI?",
  "count": 3,
  "hits": [
    { "chunk_id": "…", "source_title": "Fundamentals of Remote Sensing …",
      "page_start": 25, "page_end": 25, "section": null,
      "score": 0.70, "text": "Remote sensing is …" }
  ]
}
```
`score` = cosine similarity (higher = closer).

```bash
curl -X POST http://127.0.0.1:8000/api/v1/search \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"What is NDVI?","k":3}'
```

### 4.3 `POST /api/v1/chat` — grounded, cited answer (auth)

Same body as search; **two representations** via the `Accept` header.

**Request**
```json
{ "question": "What is remote sensing?", "k": 4 }
```

**(a) Buffered JSON** — `Accept: application/json` (Swagger default), `200`:
```json
{
  "answer": "Remote sensing is the science of … [S1]",
  "citations": [
    { "marker": "S1", "chunk_id": "…", "source_title": "Fundamentals of Remote Sensing …",
      "page_start": 25, "section": null, "score": 0.70 }
  ],
  "insufficient_evidence": false
}
```
The `[S1]` markers in `answer` map to the `citations` array. If the corpus
doesn't cover the question, `answer` is the refusal and `insufficient_evidence`
is `true`.

**(b) SSE stream** — `Accept: text/event-stream` (use `curl -N`, not Swagger):
```
event: start
data: {"model":"gpt-4o","retrieved":4}

event: delta
data: {"text":"Remote"}
… (many delta events, token by token) …

event: citations
data: {"citations":[{"marker":"S1","source_title":"…","page_start":25,…}]}

event: usage
data: {"prompt_tokens":1840,"completion_tokens":320,"ttft_ms":380}

event: done
data: {"finish_reason":"stop","insufficient_evidence":false}
```

```bash
# buffered
curl -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"What is remote sensing?","k":4}'

# streaming (note -N and the Accept header)
curl -N -X POST http://127.0.0.1:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"question":"What is remote sensing?","k":4}'
```
> Swagger shows the buffered JSON. To see live streaming, use the `curl -N`
> command above.

### 4.4 Documents (admin — `is_admin` required)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/documents` | Upload a PDF → object store + register |
| POST | `/api/v1/documents/{version_id}/ingest` | Enqueue ingestion job |
| GET | `/api/v1/documents/{version_id}/ingest/status` | Job status + chunk count |
| GET | `/api/v1/documents` | List documents |

**Upload — `POST /api/v1/documents`** (multipart form, field `file`):

Response `201`:
```json
{ "document_id": "…", "version_id": "…", "version_no": 1,
  "title": "Reddy_RS_GIS", "status": "pending" }
```
In Swagger: expand the endpoint → **Try it out** → choose a PDF for `file` → Execute.
```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN" -F "file=@book.pdf"
```

**Ingest — `POST /api/v1/documents/{version_id}/ingest`** (optional `?max_pages=N`):

Response `202` + `Location` header:
```json
{ "version_id": "…", "status": "queued" }
```
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/documents/<version_id>/ingest?max_pages=12" \
  -H "Authorization: Bearer $TOKEN"
```
> A **worker must be running** to process the job (`python scripts/run_worker.py`).

**Status — `GET /api/v1/documents/{version_id}/ingest/status`**:
```json
{ "version_id": "…", "status": "published", "chunks": 11 }
```
Statuses: `pending → queued → ingesting → published` (or `quarantined` if no
text was extractable, e.g. a scanned PDF with no OCR).

**List — `GET /api/v1/documents`**:
```json
[ { "id": "…", "title": "Reddy_RS_GIS", "is_active": true,
    "allowed_for_rag": true, "status": "published" } ]
```

### 4.5 Auth

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/v1/auth/dev-login` | open (needs `DEV_AUTH=true`) | Issue a JWT for a `@thaarei.com` email (dev only) |
| GET | `/api/v1/me` | Bearer | Current user `{user_id, email, is_admin}` |

```json
// POST /api/v1/auth/dev-login   body:
{ "email": "devavirathan@thaarei.com" }
// 200 ->
{ "access_token": "<jwt>", "token_type": "bearer", "email": "…", "is_admin": true }
```

---

## 5. End-to-end flows

### Flow A — Ask a question (any employee)
1. **Authorize** with a `@thaarei.com` token.
2. `POST /api/v1/search` to see raw chunks, **or** `POST /api/v1/chat` for a cited answer.

### Flow B — Add a document (admin)
1. Ensure a **worker is running** and you have an **admin** token.
2. `POST /api/v1/documents` (upload PDF) → note `version_id`.
3. `POST /api/v1/documents/{version_id}/ingest?max_pages=12` → `202 queued`.
4. `GET /api/v1/documents/{version_id}/ingest/status` → wait for `published`.
5. `POST /api/v1/chat` a question the document covers → answer cites it.

---

## 6. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `401` | No/expired token — re-Authorize with a fresh `dev_token.py` token. |
| `403` | Token domain isn't `@thaarei.com`, or route needs `is_admin` (set it in the DB). |
| `500` on `/search` or `/chat` | Usually a missing/invalid `OPENAI_API_KEY` in `.env`. |
| `readyz` = `unavailable` | Postgres not up — `docker compose up -d`; check host port (5433 here). |
| ingest stuck at `queued` | No worker running — start `python scripts/run_worker.py`. |
| ingest → `quarantined` | Scanned PDF with no text layer and no Tesseract installed (OCR unavailable). |
