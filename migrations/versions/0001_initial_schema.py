"""initial schema — Plan/03 (identity, documents, chunks, embeddings, logs)

Revision ID: 0001
Revises:
Create Date: 2026-07-01

Hand-authored raw SQL: the schema uses features Alembic autogenerate can't
model (pgvector VECTOR type, citext, a GENERATED tsvector column, an updated_at
trigger, partial/unique indexes, CHECK constraints). Kept as the exact DDL from
Plan/03-vector-db-and-data-stores.md so the DB matches the design doc.
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


UPGRADE = [
    # --- Extensions (idempotent; also enabled by the docker init script) ---
    "CREATE EXTENSION IF NOT EXISTS vector",
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    "CREATE EXTENSION IF NOT EXISTS citext",
    # --- Shared updated_at trigger ---
    """CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql""",
    # --- Identity: thaarei.com employees only ---
    r"""CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         CITEXT NOT NULL UNIQUE,
    display_name  TEXT,
    is_admin      BOOLEAN NOT NULL DEFAULT FALSE,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT users_thaarei_domain CHECK (email ~* '^[^@\s]+@thaarei\.com$')
)""",
    "CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users "
    "FOR EACH ROW EXECUTE FUNCTION set_updated_at()",
    # --- Documents & versions ---
    """CREATE TABLE documents (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title             TEXT NOT NULL,
    author            TEXT, publisher TEXT, edition TEXT,
    publication_year  INT  CHECK (publication_year BETWEEN 1800 AND 2100),
    source_type       TEXT NOT NULL DEFAULT 'book'
                        CHECK (source_type IN ('book','internal_doc','api_doc')),
    license_status    TEXT NOT NULL DEFAULT 'restricted'
                        CHECK (license_status IN ('approved','restricted','denied')),
    allowed_for_rag   BOOLEAN NOT NULL DEFAULT FALSE,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    checksum          TEXT NOT NULL UNIQUE,
    file_path         TEXT NOT NULL,
    uploaded_by       UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    "CREATE TRIGGER trg_documents_updated BEFORE UPDATE ON documents "
    "FOR EACH ROW EXECUTE FUNCTION set_updated_at()",
    """CREATE TABLE document_versions (
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
)""",
    # At most one published version per document (also serves the retrieval join).
    "CREATE UNIQUE INDEX one_published_version_per_doc "
    "ON document_versions (document_id) WHERE status = 'published'",
    # --- Chunks & embeddings ---
    """CREATE TABLE chunks (
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
    tsv tsvector GENERATED ALWAYS AS
        (to_tsvector('english', coalesce(heading_path,'') || ' ' || text)) STORED,
    UNIQUE (document_version_id, chunk_index),
    CHECK (page_end IS NULL OR page_start IS NULL OR page_end >= page_start)
)""",
    """CREATE TABLE chunk_embeddings (
    chunk_id        UUID PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
    embedding_model TEXT NOT NULL,
    embedding_dim   INT  NOT NULL,
    embedding       VECTOR(1536) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    # --- Chat history, observability, quality ---
    """CREATE TABLE conversations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """CREATE TABLE query_logs (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id       UUID REFERENCES conversations(id) ON DELETE SET NULL,
    user_id               UUID REFERENCES users(id) ON DELETE SET NULL,
    question              TEXT NOT NULL,
    rewritten_query       TEXT, intent TEXT, filters JSONB,
    retrieved_chunk_ids   UUID[], cited_chunk_ids UUID[],
    answer                TEXT, model_name TEXT,
    prompt_tokens         INT, completion_tokens INT, cost_usd NUMERIC(10,4),
    latency_ms            INT,
    insufficient_evidence BOOLEAN,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """CREATE TABLE feedback (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_log_id  UUID NOT NULL REFERENCES query_logs(id) ON DELETE CASCADE,
    user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    rating        SMALLINT CHECK (rating IN (-1, 1)),
    issue_type    TEXT, comment TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """CREATE TABLE audit_log (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT NOT NULL,
    entity     TEXT, entity_id TEXT,
    detail     JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    # --- Glossary & evaluation (carried over from appendix §15) ---
    """CREATE TABLE glossary_terms (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    term                  TEXT NOT NULL UNIQUE,
    acronym               TEXT,
    definition            TEXT NOT NULL,
    simple_explanation    TEXT,
    developer_explanation TEXT,
    related_terms         TEXT[],
    validated_by_expert   BOOLEAN NOT NULL DEFAULT FALSE,
    source_chunk_ids      UUID[],
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    "CREATE TRIGGER trg_glossary_updated BEFORE UPDATE ON glossary_terms "
    "FOR EACH ROW EXECUTE FUNCTION set_updated_at()",
    """CREATE TABLE eval_questions (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question               TEXT NOT NULL,
    expected_answer        TEXT,
    expected_source_titles TEXT[],
    expected_terms         TEXT[],
    difficulty             TEXT,
    category               TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    # --- Indexes ---
    "CREATE INDEX idx_emb_hnsw ON chunk_embeddings USING hnsw (embedding vector_cosine_ops)",
    "CREATE INDEX idx_chunks_tsv ON chunks USING gin (tsv)",
    "CREATE INDEX idx_chunks_document ON chunks (document_id)",
    "CREATE INDEX idx_chunks_tags ON chunks USING gin (tags)",
    "CREATE INDEX idx_chunks_domain ON chunks (domain)",
    "CREATE INDEX idx_qlogs_user_time ON query_logs (user_id, created_at DESC)",
]

DOWNGRADE = [
    "DROP TABLE IF EXISTS eval_questions CASCADE",
    "DROP TABLE IF EXISTS glossary_terms CASCADE",
    "DROP TABLE IF EXISTS audit_log CASCADE",
    "DROP TABLE IF EXISTS feedback CASCADE",
    "DROP TABLE IF EXISTS query_logs CASCADE",
    "DROP TABLE IF EXISTS conversations CASCADE",
    "DROP TABLE IF EXISTS chunk_embeddings CASCADE",
    "DROP TABLE IF EXISTS chunks CASCADE",
    "DROP TABLE IF EXISTS document_versions CASCADE",
    "DROP TABLE IF EXISTS documents CASCADE",
    "DROP TABLE IF EXISTS users CASCADE",
    "DROP FUNCTION IF EXISTS set_updated_at()",
]


def upgrade() -> None:
    for stmt in UPGRADE:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in DOWNGRADE:
        op.execute(stmt)
