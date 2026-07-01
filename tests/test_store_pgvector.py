"""Integration test for the pgvector VectorStore.

Auto-skips when Postgres isn't reachable, so offline unit runs stay green.
Needs the schema from migration 0001 (`docker compose up -d` + `alembic upgrade head`).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

psycopg = pytest.importorskip("psycopg")

from akasha.config import DATABASE_URL, EMBED_DIM  # noqa: E402
from akasha.index.store import VectorStore, _psycopg_dsn  # noqa: E402
from akasha.types import Chunk  # noqa: E402


def _db_reachable() -> bool:
    try:
        with psycopg.connect(_psycopg_dsn(DATABASE_URL), connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_reachable(), reason="Postgres not reachable")


def _unit(i: int) -> list[float]:
    """A unit vector with 1.0 at position i — a distinct direction per chunk."""
    v = [0.0] * EMBED_DIM
    v[i] = 1.0
    return v


def test_add_and_query_orders_by_similarity():
    store = VectorStore()
    conn = psycopg.connect(_psycopg_dsn(DATABASE_URL), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, allowed_for_rag, is_active, checksum, file_path) "
            "VALUES ('TEST DOC', true, true, %s, 's3://test') RETURNING id",
            ("chk-" + uuid.uuid4().hex,),
        )
        doc_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO document_versions (document_id, version_no, file_path, checksum, status) "
            "VALUES (%s, 1, 's3://test', %s, 'published') RETURNING id",
            (doc_id, "chk-" + uuid.uuid4().hex),
        )
        ver_id = cur.fetchone()[0]

    try:
        chunks = [
            Chunk(
                document_id=doc_id,
                document_version_id=ver_id,
                chunk_index=i,
                text=f"chunk {i}",
                page_start=i + 1,
            )
            for i in range(3)
        ]
        store.add(chunks, [_unit(0), _unit(1), _unit(2)])

        results = store.query(_unit(0), k=3)
        assert len(results) == 3
        # Query vector == chunk 0's vector → ranks first with ~1.0 similarity.
        assert results[0].chunk.text == "chunk 0"
        assert results[0].chunk.source_title == "TEST DOC"
        assert results[0].chunk.page_start == 1
        assert results[0].score == pytest.approx(1.0, abs=1e-3)

        # Idempotent: re-adding the same chunks updates in place, no duplicates.
        store.add(chunks, [_unit(0), _unit(1), _unit(2)])
        assert len(store.query(_unit(0), k=10)) == 3
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))  # cascades
        conn.close()
        store.close()


def test_query_excludes_unpublished_documents():
    """A chunk under a non-published version must not be retrievable."""
    store = VectorStore()
    conn = psycopg.connect(_psycopg_dsn(DATABASE_URL), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, allowed_for_rag, is_active, checksum, file_path) "
            "VALUES ('DRAFT DOC', true, true, %s, 's3://d') RETURNING id",
            ("chk-" + uuid.uuid4().hex,),
        )
        doc_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO document_versions (document_id, version_no, file_path, checksum, status) "
            "VALUES (%s, 1, 's3://d', %s, 'pending') RETURNING id",
            (doc_id, "chk-" + uuid.uuid4().hex),
        )
        ver_id = cur.fetchone()[0]
    try:
        store.add(
            [Chunk(document_id=doc_id, document_version_id=ver_id, chunk_index=0, text="hidden")],
            [_unit(5)],
        )
        titles = [r.chunk.source_title for r in store.query(_unit(5), k=10)]
        assert "DRAFT DOC" not in titles
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.close()
        store.close()
