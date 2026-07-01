# 3. Vector DB & Data Stores

[← Ingestion](02-ingestion-pipeline.md) · [Index](README.md) · Next: [Backend APIs →](04-backend-apis.md)

Three team-owned stores implement the production-control thesis. Keeping vectors
_inside_ PostgreSQL is the key decision: it lets governance and metadata filters
run as ordinary SQL joined against the same rows retrieval scores.

## 3.1 The three stores

| Store | Holds | Tech |
|-------|-------|------|
| Document store | Raw PDFs + extracted/normalized text artifacts | Object storage (MinIO / S3 / GCS) |
| Metadata DB | Documents, versions, chunks, users (`@thaarei.com`), conversations, logs, feedback, evals, audit | PostgreSQL 16 |
| Vector DB | Chunk embeddings | pgvector extension in the same PostgreSQL |

## 3.2 Why pgvector as primary

- **Governance & metadata filters are just SQL.** The "published + RAG-approved"
  gate and book/tag filters join to chunks in the same query that scores vectors.
- **Book-wise / metadata search** uses normal indexed columns.
- **Transactional consistency** between a chunk and its vector (one DB, one
  version lifecycle).
- **Operational simplicity** — one engine to back up, migrate, secure.

Qdrant remains the documented scale-out path ([§3.8](#38-when-to-move-off-pgvector)).

## 3.3 Access model — `@thaarei.com` employees only

**There is no role hierarchy.** Every authenticated, active `@thaarei.com`
employee is an equal user of the RAG with identical, full read access to the
whole approved corpus. Access control therefore collapses to **authentication**:
_are you a current thaarei.com employee?_ This is enforced in **three layers**
(defense in depth):

1. **Identity provider** — sign-in is restricted to the thaarei.com workspace
   tenant (e.g. Google Workspace `hd=thaarei.com` / Microsoft 365 single-tenant),
   so no external account can even obtain a token. This is the primary gate.
2. **Application** — on every request the API validates the JWT and rejects any
   token whose `email` is not a verified `@thaarei.com` address
   ([05-security.md](05-security.md#51-authentication--the-thaareicom-gate)).
3. **Database** — a `CHECK` constraint makes a non-`@thaarei.com` row
   physically un-insertable, so even a bug or bad seed can't create a foreign
   account.

The only distinction between users is a single **`is_admin` boolean flag** — not
a role system — marking who may upload/ingest/govern the corpus. All employees,
admin or not, query with the same full visibility. (If even that isn't needed,
drop the flag and gate admin actions at the network layer.)

## 3.4 Schema

Professional conventions applied throughout: `gen_random_uuid()` PKs,
`TIMESTAMPTZ` everywhere, `CHECK`-constrained status/enum columns (kept as
`TEXT` for migration flexibility), explicit `ON DELETE` behaviour, a generated
`tsv` column, an `updated_at` trigger, and natural `UNIQUE` keys for idempotent
ingestion.

```sql
-- Extensions ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;    -- pgvector: VECTOR type + ANN indexes
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;    -- case-insensitive, unique emails

-- Shared updated_at trigger --------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

-- Identity: thaarei.com employees only ---------------------------------
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         CITEXT NOT NULL UNIQUE,          -- case-insensitive uniqueness
    display_name  TEXT,
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,  -- corpus admin flag, NOT a role tier
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,   -- set FALSE on offboarding
    last_login_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Hard domain gate: only employee_name@thaarei.com may exist. Rejects any
    -- other domain and subdomains (e.g. @sub.thaarei.com) by design.
    CONSTRAINT users_thaarei_domain
        CHECK (email ~* '^[^@\s]+@thaarei\.com$')
);
CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Documents & versions --------------------------------------------------
CREATE TABLE documents (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title             TEXT NOT NULL,
    author            TEXT, publisher TEXT, edition TEXT,
    publication_year  INT  CHECK (publication_year BETWEEN 1800 AND 2100),
    source_type       TEXT NOT NULL DEFAULT 'book'
                        CHECK (source_type IN ('book','internal_doc','api_doc')),
    license_status    TEXT NOT NULL DEFAULT 'restricted'
                        CHECK (license_status IN ('approved','restricted','denied')),
    allowed_for_rag   BOOLEAN NOT NULL DEFAULT FALSE,  -- governance gate (legality)
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,   -- soft-disable from retrieval
    checksum          TEXT NOT NULL UNIQUE,            -- document-level dedup
    file_path         TEXT NOT NULL,                   -- object-storage key
    uploaded_by       UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_documents_updated BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE document_versions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_no    INT  NOT NULL,
    file_path     TEXT NOT NULL,
    checksum      TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','ingesting','qa',
                                      'published','retired','quarantined')),
    ingested_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_no),
    UNIQUE (document_id, checksum)
);
-- Enforce at most ONE published version per document.
CREATE UNIQUE INDEX one_published_version_per_doc
    ON document_versions (document_id) WHERE status = 'published';

-- Chunks & embeddings ---------------------------------------------------
CREATE TABLE chunks (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id          UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    document_version_id  UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    chunk_index          INT  NOT NULL,
    page_start           INT, page_end INT,
    chapter TEXT, section TEXT, heading_path TEXT,
    text                 TEXT NOT NULL,
    token_count          INT,
    domain TEXT, difficulty TEXT, tags TEXT[],
    is_ocr               BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Generated keyword vector (heading context + body); no write-time trigger.
    tsv tsvector GENERATED ALWAYS AS
        (to_tsvector('english', coalesce(heading_path,'') || ' ' || text)) STORED,
    UNIQUE (document_version_id, chunk_index),
    CHECK (page_end IS NULL OR page_start IS NULL OR page_end >= page_start)
);

CREATE TABLE chunk_embeddings (
    chunk_id        UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    embedding_dim   INT  NOT NULL,
    -- 1536 = HNSW-indexable (pgvector caps ANN indexes at 2000 dims). See §3.6.
    embedding       VECTOR(1536) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Chat history, observability, quality ---------------------------------
CREATE TABLE conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE query_logs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id       UUID REFERENCES conversations(id) ON DELETE SET NULL,
    user_id               UUID REFERENCES users(id) ON DELETE SET NULL,  -- keep logs if user removed
    question              TEXT NOT NULL,
    rewritten_query       TEXT, intent TEXT, filters JSONB,
    retrieved_chunk_ids   UUID[], cited_chunk_ids UUID[],
    answer                TEXT, model_name TEXT,
    prompt_tokens         INT, completion_tokens INT, cost_usd NUMERIC(10,4),
    latency_ms            INT,
    insufficient_evidence BOOLEAN,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE feedback (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id  UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    rating        SMALLINT CHECK (rating IN (-1, 1)),   -- thumbs down / up
    issue_type    TEXT, comment TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Append-only audit trail (uploads, ingests, user activation, etc.) -----
CREATE TABLE audit_log (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT NOT NULL,       -- 'document.upload' | 'document.ingest' | 'user.deactivate' | ...
    entity     TEXT, entity_id TEXT,
    detail     JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Glossary and eval tables carry over unchanged from the
[appendix, §15](appendix-domain-reference.md#15-database-design).

### Provisioning an employee account

```sql
-- Allowed: a thaarei.com employee
INSERT INTO users (email, display_name)
VALUES ('devavirathan@thaarei.com', 'Deva Virathan');

-- Grant corpus-admin (uploads/ingestion) to a specific employee
UPDATE users SET is_admin = TRUE WHERE email = 'devavirathan@thaarei.com';

-- Rejected by users_thaarei_domain CHECK — cannot be inserted at all:
INSERT INTO users (email) VALUES ('someone@gmail.com');
--> ERROR:  new row for relation "users" violates check constraint "users_thaarei_domain"
```

In practice accounts are created automatically on first SSO login (just-in-time
provisioning) once the IdP has confirmed the thaarei.com identity — the manual
`INSERT` above is for seeding/admin bootstrap.

## 3.5 Indexes

```sql
-- Vector ANN (build AFTER bulk load for speed). Requires dim <= 2000 (§3.6).
CREATE INDEX idx_emb_hnsw ON chunk_embeddings
    USING hnsw (embedding vector_cosine_ops);
-- Keyword / hybrid
CREATE INDEX idx_chunks_tsv ON chunks USING gin (tsv);
-- Metadata & book-wise filters
CREATE INDEX idx_chunks_document ON chunks (document_id);
CREATE INDEX idx_chunks_tags     ON chunks USING gin (tags);
CREATE INDEX idx_chunks_domain   ON chunks (domain);
-- Retrieval join: fast lookup of the single published version
CREATE INDEX idx_docver_published ON document_versions (document_id)
    WHERE status = 'published';
-- Chat history
CREATE INDEX idx_qlogs_user_time ON query_logs (user_id, created_at DESC);
```

Distance metric: **cosine** (typical for OpenAI embeddings — confirm during
validation).

## 3.6 Embedding dimensions — the pgvector 2000-dim ceiling ⚠️

pgvector can **store** vectors up to ~16k dims, but its **ANN indexes (HNSW /
IVFFlat) support at most 2000 dimensions**. `text-embedding-3-large` defaults to
**3072** → not indexable → every search would fall back to a full sequential
scan. So we standardize on **1536-dim vectors**, which are natively HNSW-indexable:

- **Recommended:** `text-embedding-3-small` (native 1536), or
- `text-embedding-3-large` with the OpenAI `dimensions` parameter set to
  `1536` (or `2000`) — v3 models support shortening with minimal quality loss.

Set `EMBED_DIM = 1536` in [config](../src/akasha/config.py) so it matches the
`VECTOR(1536)` column, and **lock it before the first migration** — the column
dimension is fixed at creation ([§3.9](#39-sizing-backups-migrations)). This is
the concrete resolution of the [validation item](README.md#validate-before-locking).

## 3.7 Retrieval query (governance filter, no per-user ACL)

Because access is settled at authentication ([§3.3](#33-access-model--thaareicom-employees-only)),
retrieval enforces only **corpus governance** — published, active, RAG-approved
— plus optional book/tag filters. There is no ACL join:

```sql
SELECT c.id, c.text, c.page_start, c.page_end, c.chapter, c.section,
       c.document_id, d.title AS source_title,
       e.embedding <=> :query_vec AS distance
FROM chunks c
JOIN chunk_embeddings e  ON e.chunk_id = c.id
JOIN document_versions v ON v.id = c.document_version_id AND v.status = 'published'
JOIN documents d         ON d.id = c.document_id
                        AND d.is_active AND d.allowed_for_rag
WHERE (:book_ids IS NULL OR c.document_id = ANY(:book_ids))   -- book-wise search
  AND (:tags     IS NULL OR c.tags && :tags)                  -- metadata filter
ORDER BY distance
LIMIT :k;
```

Delivers **book-wise search** and **metadata filtering**; per-user visibility is
uniform, so it isn't in the WHERE clause.

## 3.8 Hybrid search

Run vector search (above) **and** keyword search over `tsv` in parallel, then
fuse with **Reciprocal Rank Fusion**. Keyword search is essential here because
GIS terms are short acronyms (`NDVI`, `COG`, `STAC`, `LISS-III`, `SAR`) that
semantic search alone can miss — see [appendix §12.3](appendix-domain-reference.md#123-hybrid-search-recommendation).
Orchestration + reranking: [04-backend-apis.md](04-backend-apis.md#44-rag-orchestrator).

## 3.9 Citation tracking

Because chunks retain `document_id`, `page_start/end`, `chapter`, `section`, and
retrieval returns chunk ids, the answer's citations are exact and verifiable.
`query_logs.cited_chunk_ids` vs `retrieved_chunk_ids` records which retrieved
chunks the model actually used — the substrate for **citation-accuracy
evaluation** ([07](07-evaluation.md)).

## 3.10 When to move off pgvector

Move to **Qdrant** (or similar) only when: dataset ≫ a few million vectors,
sustained vector QPS strains PostgreSQL, or you need advanced vector features
(named vectors, quantization at scale). Keep PostgreSQL as the identity/metadata
source of truth and mirror ids into Qdrant.

## 3.11 Sizing, backups, migrations

- **Sizing:** ~1.2 GB of text → low-hundreds-of-thousands of chunks → a few GB
  of 1536-dim vectors; trivial for one PostgreSQL instance.
- **Backups:** nightly `pg_dump` + PITR (WAL archiving); object storage
  versioning for raw PDFs. DR detail in [06](06-deployment.md).
- **Migrations:** Alembic; the `VECTOR(n)` dimension is fixed at first migration
  — **lock `EMBED_DIM = 1536` before the initial migration** to avoid a reindex.

## 3.12 Scaffold changes required

Update the earlier scaffold to this design: `index/store.py` → pgvector
(`psycopg`/SQLAlchemy) instead of Chroma; `index/embed.py` → OpenAI; `config.py`
→ `OPENAI_*`, `EMBED_DIM=1536`, `DATABASE_URL`.
