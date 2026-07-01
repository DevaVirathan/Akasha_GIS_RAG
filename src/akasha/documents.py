"""Document + version DB operations (the document service data layer)."""

from __future__ import annotations

import uuid

from .config import DATABASE_URL
from .index.store import _psycopg_dsn


def _conn():
    import psycopg

    return psycopg.connect(_psycopg_dsn(DATABASE_URL), autocommit=True)


def _uuid(x) -> uuid.UUID:
    return x if isinstance(x, uuid.UUID) else uuid.UUID(str(x))


def register_document(title: str, checksum: str, object_key: str, uploaded_by) -> tuple:
    """Upsert a document (dedup on checksum) + its v1 (status 'pending')."""
    ub = _uuid(uploaded_by) if uploaded_by else None
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, source_type, license_status, allowed_for_rag, "
            "is_active, checksum, file_path, uploaded_by) "
            "VALUES (%s,'book','approved',true,true,%s,%s,%s) "
            "ON CONFLICT (checksum) DO UPDATE SET updated_at=now() RETURNING id",
            (title, checksum, object_key, ub),
        )
        doc_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO document_versions (document_id, version_no, file_path, checksum, status) "
            "VALUES (%s,1,%s,%s,'pending') "
            "ON CONFLICT (document_id, version_no) "
            "DO UPDATE SET status='pending', file_path=EXCLUDED.file_path RETURNING id, version_no",
            (doc_id, object_key, checksum),
        )
        ver_id, ver_no = cur.fetchone()
    return doc_id, ver_id, ver_no


def get_version(version_id) -> dict | None:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT dv.id, dv.document_id, dv.file_path, dv.status, d.title "
            "FROM document_versions dv JOIN documents d ON d.id = dv.document_id "
            "WHERE dv.id = %s",
            (_uuid(version_id),),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "document_id": row[1], "file_path": row[2], "status": row[3], "title": row[4]}


def set_version_status(version_id, status: str) -> None:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE document_versions SET status=%s, "
            "ingested_at = CASE WHEN %s='published' THEN now() ELSE ingested_at END "
            "WHERE id=%s",
            (status, status, _uuid(version_id)),
        )


def ingest_status(version_id) -> dict | None:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT dv.status, (SELECT count(*) FROM chunks c WHERE c.document_version_id = dv.id) "
            "FROM document_versions dv WHERE dv.id = %s",
            (_uuid(version_id),),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"status": row[0], "chunks": row[1]}


def list_documents(limit: int = 50) -> list[dict]:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT d.id, d.title, d.is_active, d.allowed_for_rag, "
            "(SELECT status FROM document_versions v WHERE v.document_id = d.id "
            " ORDER BY version_no DESC LIMIT 1) "
            "FROM documents d ORDER BY d.created_at DESC LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
    return [
        {"id": str(r[0]), "title": r[1], "is_active": r[2], "allowed_for_rag": r[3], "status": r[4]}
        for r in rows
    ]
