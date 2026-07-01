# 3. Vector DB & Data Stores

[← Ingestion](02-ingestion-pipeline.md) · [Index](README.md) · Next: [Backend APIs →](04-backend-apis.md)

Three team-owned stores implement the production-control thesis. Keeping vectors
_inside_ PostgreSQL is the key decision: it lets permission and metadata filters
run as ordinary SQL joined against the same rows retrieval scores.

## 3.1 The three stores

| Store | Holds | Tech |
|-------|-------|------|
| Document store | Raw PDFs + extracted/normalized text artifacts | Object storage (MinIO / S3 / GCS) |
| Metadata DB | Documents, versions, chunks, users, roles, ACLs, glossary, logs, feedback, evals | PostgreSQL 16 |
| Vector DB | Chunk embeddings | pgvector extension in the same PostgreSQL |

## 3.2 Why pgvector as primary

- **Permission filters are just SQL.** ACL rows join to chunks in the same
  query that does vector search — no cross-system consistency problem.
- **Book-wise / metadata search** uses normal indexed columns.
- **Transactional consistency** between a chunk and its vector (one DB, one
  version lifecycle).
- **Operational simplicity** — one engine to back up, migrate, secure.

Qdrant remains the documented scale-out path ([§3.8](#38-when-to-move-off-pgvector)).

## 3.3 Schema

Elevates the appendix schema and adds the **identity + ACL** tables that make
permission filtering real. Embedding dimension is a placeholder pending
[validation](README.md#validate-before-locking).

```sql
-- Identity & access -----------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE roles (
    id UUID PRIMARY KEY,
    name TEXT UNIQUE NOT NULL          -- admin | curator | developer | viewer
);

CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);

-- Documents & versions --------------------------------------------------
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT, publisher TEXT, edition TEXT, publication_year INT,
    source_type TEXT NOT NULL,          -- book | internal_doc | api_doc
    license_status TEXT NOT NULL,       -- approved | restricted | denied
    allowed_for_rag BOOLEAN DEFAULT FALSE,
    confidentiality_level TEXT DEFAULT 'internal',  -- public | internal | restricted
    file_path TEXT NOT NULL, checksum TEXT NOT NULL,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE document_versions (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    version_no INT NOT NULL,
    file_path TEXT NOT NULL, checksum TEXT NOT NULL,
    status TEXT DEFAULT 'pending',      -- pending | ingesting | qa | published | retired | quarantined
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (document_id, version_no)
);

-- Access control on documents ------------------------------------------
-- A chunk is visible to a caller if the caller's roles intersect the
-- document's grants (or the document is public). Enforced at query time.
CREATE TABLE document_acl (
    document_id UUID REFERENCES documents(id),
    role_id UUID REFERENCES roles(id),
    PRIMARY KEY (document_id, role_id)
);

-- Chunks & embeddings ---------------------------------------------------
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    document_version_id UUID REFERENCES document_versions(id),
    chunk_index INT NOT NULL,
    page_start INT, page_end INT,
    chapter TEXT, section TEXT, heading_path TEXT,
    text TEXT NOT NULL,
    tsv tsvector,                       -- keyword/BM25-style search
    token_count INT,
    domain TEXT, difficulty TEXT, tags TEXT[],
    is_ocr BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chunk_embeddings (
    chunk_id UUID PRIMARY KEY REFERENCES chunks(id),
    embedding_model TEXT NOT NULL,
    embedding_dim INT NOT NULL,
    embedding VECTOR(3072),             -- VALIDATE: match OPENAI_EMBEDDING_MODEL output dim
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Observability & quality ----------------------------------------------
CREATE TABLE query_logs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    question TEXT NOT NULL, rewritten_query TEXT, intent TEXT,
    filters JSONB,
    retrieved_chunk_ids UUID[], cited_chunk_ids UUID[],
    answer TEXT, model_name TEXT,
    prompt_tokens INT, completion_tokens INT, cost_usd NUMERIC,
    latency_ms INT, created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE feedback (
    id UUID PRIMARY KEY,
    query_log_id UUID REFERENCES query_logs(id),
    user_id UUID REFERENCES users(id),
    rating INT, issue_type TEXT, comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Glossary and eval tables carry over unchanged from the
[appendix, §15](appendix-domain-reference.md#15-database-design).

## 3.4 Indexes

```sql
-- Vector index (HNSW recommended for recall/latency; VALIDATE opclass vs dim)
CREATE INDEX ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);
-- Keyword search
CREATE INDEX ON chunks USING gin (tsv);
-- Metadata / book-wise filters
CREATE INDEX ON chunks (document_id);
CREATE INDEX ON chunks USING gin (tags);
CREATE INDEX ON chunks (domain);
```

Distance metric: **cosine** (typical for OpenAI embeddings — confirm during
validation). Populate `tsv` on write (trigger or app-side).

## 3.5 Permission filtering at query time

The retriever restricts candidates to documents the caller may read, **before**
ranking — so a user never even scores a forbidden chunk:

```sql
WITH allowed AS (
  SELECT d.id FROM documents d
  WHERE d.confidentiality_level = 'public'
     OR d.id IN (SELECT document_id FROM document_acl a
                 JOIN user_roles ur ON ur.role_id = a.role_id
                 WHERE ur.user_id = :caller)
)
SELECT c.id, c.text, c.page_start, c.section, c.document_id,
       e.embedding <=> :query_vec AS distance
FROM chunks c
JOIN chunk_embeddings e ON e.chunk_id = c.id
JOIN document_versions v ON v.id = c.document_version_id AND v.status = 'published'
WHERE c.document_id IN (SELECT id FROM allowed)
  AND (:book_ids IS NULL OR c.document_id = ANY(:book_ids))   -- book-wise search
  AND (:tags     IS NULL OR c.tags && :tags)                  -- metadata filter
ORDER BY distance
LIMIT :k;
```

This single query delivers three of the four headline capabilities:
**permission filters**, **book-wise search**, and metadata filtering.

## 3.6 Hybrid search

Run vector search (above) **and** keyword search over `tsv` in parallel, then
fuse with **Reciprocal Rank Fusion**. Keyword search is essential here because
GIS terms are short acronyms (`NDVI`, `COG`, `STAC`, `LISS-III`, `SAR`) that
semantic search alone can miss — see [appendix §12.3](appendix-domain-reference.md#123-hybrid-search-recommendation).
Orchestration + reranking: [04-backend-apis.md](04-backend-apis.md#45-rag-orchestrator).

## 3.7 Citation tracking

Because chunks retain `document_id`, `page_start/end`, `chapter`, `section`, and
retrieval returns chunk ids, the answer's citations are exact and verifiable.
`query_logs.cited_chunk_ids` records which retrieved chunks the model actually
used — the substrate for **citation-accuracy evaluation** ([07](07-evaluation.md)).

## 3.8 When to move off pgvector

Move to **Qdrant** (or similar) only when: dataset ≫ a few million vectors,
sustained vector QPS strains PostgreSQL, or you need advanced vector features
(named vectors, quantization at scale). At that point keep PostgreSQL as the
metadata/ACL source of truth and mirror ids into Qdrant, filtering by an
allow-list resolved from PostgreSQL first.

## 3.9 Sizing, backups, migrations

- **Sizing:** ~1.2 GB of text → low-hundreds-of-thousands of chunks → a few GB
  of vectors at full dimensionality; trivial for one PostgreSQL instance.
- **Backups:** nightly `pg_dump` + PITR (WAL archiving); object storage
  versioning for raw PDFs. DR detail in [06](06-deployment.md).
- **Migrations:** Alembic; the `VECTOR(n)` dimension is fixed at first migration
  — **lock `EMBED_DIM` before the initial migration** to avoid a reindex.

## 3.10 Scaffold changes required

Update the earlier scaffold to this design: `index/store.py` → pgvector
(`psycopg`/SQLAlchemy) instead of Chroma; `index/embed.py` → OpenAI instead of
Voyage; `config.py` → `OPENAI_*` + `DATABASE_URL`.
