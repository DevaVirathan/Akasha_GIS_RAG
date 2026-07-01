"""Ingestion job: pull a version's PDF from object storage and index it.

Run by the worker (scripts/run_worker.py). Mirrors scripts/run_ingest.py but
sources bytes from MinIO and updates the version's status through the lifecycle.
"""

from __future__ import annotations

from .. import objectstore
from ..documents import get_version, set_version_status
from ..index.embed import embed_texts
from ..index.store import VectorStore
from .chunk import chunk_pages
from .extract import extract_pdf_bytes


def ingest_version(version_id, max_pages: int | None = None) -> int:
    """Extract → chunk → embed → store → publish. Returns the chunk count."""
    version = get_version(version_id)
    if version is None:
        raise ValueError(f"document version {version_id} not found")

    set_version_status(version_id, "ingesting")
    data = objectstore.get_bytes(version["file_path"])
    pages = extract_pdf_bytes(data, source_file=version["title"], max_pages=max_pages)
    chunks = chunk_pages(pages, version["document_id"], version["id"])
    if not chunks:
        set_version_status(version_id, "quarantined")
        return 0

    vectors = embed_texts([c.text for c in chunks])
    store = VectorStore()
    try:
        store.add(chunks, vectors)
    finally:
        store.close()

    set_version_status(version_id, "published")
    return len(chunks)
