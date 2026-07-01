"""Stage 4 — persist chunks + embeddings in PostgreSQL + pgvector.

Replaces the earlier Chroma scaffold. Targets the schema from Plan/03
(migration 0001): `chunks` + `chunk_embeddings`. psycopg is imported lazily so
importing this module doesn't require the driver to be installed.
"""

from __future__ import annotations

from ..config import DATABASE_URL, EMBED_MODEL, TOP_K
from ..types import Chunk, Retrieved


def _psycopg_dsn(url: str) -> str:
    """Convert a SQLAlchemy-style URL (postgresql+psycopg://…) to a libpq DSN."""
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://", "postgres+psycopg://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def _vector_literal(embedding: list[float]) -> str:
    """pgvector text form '[0.1,0.2,...]'; cast with ::vector at the call site."""
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


_CHUNK_UPSERT = """
INSERT INTO chunks (
    document_id, document_version_id, chunk_index, text,
    page_start, page_end, chapter, section, heading_path,
    token_count, domain, difficulty, tags, is_ocr
) VALUES (
    %(document_id)s, %(document_version_id)s, %(chunk_index)s, %(text)s,
    %(page_start)s, %(page_end)s, %(chapter)s, %(section)s, %(heading_path)s,
    %(token_count)s, %(domain)s, %(difficulty)s, %(tags)s, %(is_ocr)s
)
ON CONFLICT (document_version_id, chunk_index) DO UPDATE SET
    text = EXCLUDED.text, page_start = EXCLUDED.page_start,
    page_end = EXCLUDED.page_end, chapter = EXCLUDED.chapter,
    section = EXCLUDED.section, heading_path = EXCLUDED.heading_path,
    token_count = EXCLUDED.token_count, domain = EXCLUDED.domain,
    difficulty = EXCLUDED.difficulty, tags = EXCLUDED.tags, is_ocr = EXCLUDED.is_ocr
RETURNING id
"""

_EMB_UPSERT = """
INSERT INTO chunk_embeddings (chunk_id, embedding_model, embedding_dim, embedding)
VALUES (%(chunk_id)s, %(model)s, %(dim)s, %(emb)s::vector)
ON CONFLICT (chunk_id) DO UPDATE SET
    embedding_model = EXCLUDED.embedding_model,
    embedding_dim = EXCLUDED.embedding_dim,
    embedding = EXCLUDED.embedding
"""

# Governance-filtered ANN search (Plan/03 §3.7): published + active + RAG-approved.
_QUERY = """
SELECT c.id, c.document_id, c.document_version_id, c.chunk_index, c.text,
       c.page_start, c.page_end, c.chapter, c.section, c.heading_path,
       c.token_count, c.domain, c.difficulty, c.tags, c.is_ocr,
       d.title AS source_title,
       (e.embedding <=> %(q)s::vector) AS distance
FROM chunks c
JOIN chunk_embeddings e  ON e.chunk_id = c.id
JOIN document_versions v ON v.id = c.document_version_id AND v.status = 'published'
JOIN documents d         ON d.id = c.document_id AND d.is_active AND d.allowed_for_rag
ORDER BY distance
LIMIT %(k)s
"""


class VectorStore:
    """PostgreSQL + pgvector store for chunks and their embeddings."""

    def __init__(self, dsn: str = DATABASE_URL, embedding_model: str = EMBED_MODEL) -> None:
        self._dsn = _psycopg_dsn(dsn)
        self._embedding_model = embedding_model
        self._conn = None

    def _connection(self):
        import psycopg  # lazy: importing this module shouldn't require the driver

        if self._conn is None or self._conn.closed:
            # autocommit so a read (query) never lingers as an "idle in transaction"
            # holding locks; add() still gets atomicity via its conn.transaction() block.
            self._conn = psycopg.connect(self._dsn, autocommit=True)
        return self._conn

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """Upsert chunks and their vectors in one transaction. Idempotent on
        (document_version_id, chunk_index), so re-ingestion updates in place."""
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
            )
        conn = self._connection()
        with conn.transaction(), conn.cursor() as cur:
            for ch, emb in zip(chunks, embeddings):
                cur.execute(
                    _CHUNK_UPSERT,
                    {
                        "document_id": ch.document_id,
                        "document_version_id": ch.document_version_id,
                        "chunk_index": ch.chunk_index,
                        "text": ch.text,
                        "page_start": ch.page_start,
                        "page_end": ch.page_end,
                        "chapter": ch.chapter,
                        "section": ch.section,
                        "heading_path": ch.heading_path,
                        "token_count": ch.token_count,
                        "domain": ch.domain,
                        "difficulty": ch.difficulty,
                        "tags": ch.tags,
                        "is_ocr": ch.is_ocr,
                    },
                )
                chunk_id = cur.fetchone()[0]
                cur.execute(
                    _EMB_UPSERT,
                    {
                        "chunk_id": chunk_id,
                        "model": self._embedding_model,
                        "dim": len(emb),
                        "emb": _vector_literal(emb),
                    },
                )

    def query(self, embedding: list[float], k: int = TOP_K) -> list[Retrieved]:
        """Top-k most similar chunks among published, RAG-approved documents.

        `score` is cosine similarity (1 - pgvector cosine distance)."""
        conn = self._connection()
        with conn.cursor() as cur:
            cur.execute(_QUERY, {"q": _vector_literal(embedding), "k": k})
            rows = cur.fetchall()
        results: list[Retrieved] = []
        for r in rows:
            chunk = Chunk(
                document_id=r[1],
                document_version_id=r[2],
                chunk_index=r[3],
                text=r[4],
                id=str(r[0]),
                page_start=r[5],
                page_end=r[6],
                chapter=r[7],
                section=r[8],
                heading_path=r[9],
                token_count=r[10],
                domain=r[11],
                difficulty=r[12],
                tags=r[13] or [],
                is_ocr=r[14],
                source_title=r[15],
            )
            results.append(Retrieved(chunk=chunk, score=1.0 - float(r[16])))
        return results

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            self._conn = None
