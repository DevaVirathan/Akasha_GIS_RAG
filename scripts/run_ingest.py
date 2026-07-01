"""Ingest the corpus: register -> extract -> chunk -> embed -> store -> publish.

Usage (services up + `alembic upgrade head` + OPENAI_API_KEY in .env):
    python scripts/run_ingest.py --limit 1                 # first PDF
    python scripts/run_ingest.py --file "Data/.../book.pdf" --max-pages 8
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

# Make src/ importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import psycopg  # noqa: E402

from akasha.config import DATABASE_URL  # noqa: E402
from akasha.index.embed import embed_texts  # noqa: E402
from akasha.index.store import VectorStore, _psycopg_dsn  # noqa: E402
from akasha.ingest.chunk import chunk_pages  # noqa: E402
from akasha.ingest.extract import extract_pdf, iter_pdfs  # noqa: E402


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _register(conn, pdf: Path, checksum: str) -> tuple[str, str]:
    """Upsert the document + version (status 'ingesting'); return their ids.

    NOTE: dev ingest marks documents approved/allowed_for_rag and stores the
    local path as file_path. Real licensing + MinIO upload belong to the
    document service (Plan/04)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, source_type, license_status, allowed_for_rag, "
            "is_active, checksum, file_path) VALUES (%s,'book','approved',true,true,%s,%s) "
            "ON CONFLICT (checksum) DO UPDATE SET updated_at=now() RETURNING id",
            (pdf.stem, checksum, str(pdf)),
        )
        doc_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO document_versions (document_id, version_no, file_path, checksum, status) "
            "VALUES (%s,1,%s,%s,'ingesting') "
            "ON CONFLICT (document_id, version_no) DO UPDATE SET status='ingesting' RETURNING id",
            (doc_id, str(pdf), checksum),
        )
        return doc_id, cur.fetchone()[0]


def _publish(conn, version_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE document_versions SET status='published', ingested_at=now() WHERE id=%s",
            (version_id,),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the GIS/RS PDF corpus.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N PDFs.")
    parser.add_argument("--file", type=str, default=None, help="Ingest a specific PDF path.")
    parser.add_argument("--max-pages", type=int, default=None, help="Only the first N pages per PDF.")
    args = parser.parse_args()

    if args.file:
        pdfs = [Path(args.file)]
    else:
        pdfs = list(iter_pdfs())
        if args.limit is not None:
            pdfs = pdfs[: args.limit]

    conn = psycopg.connect(_psycopg_dsn(DATABASE_URL), autocommit=True)
    store = VectorStore()
    try:
        for pdf in pdfs:
            print(f"[extract] {pdf.name}")
            checksum = _checksum(pdf)
            doc_id, version_id = _register(conn, pdf, checksum)
            pages = extract_pdf(pdf, max_pages=args.max_pages)
            chunks = chunk_pages(pages, doc_id, version_id)
            if not chunks:
                print(f"[skip]    no extractable text in {pdf.name} (scanned? needs OCR)")
                continue
            vectors = embed_texts([c.text for c in chunks])
            store.add(chunks, vectors)
            _publish(conn, version_id)
            ocr = sum(1 for c in chunks if c.is_ocr)
            print(f"[stored]  {len(chunks)} chunks ({ocr} via OCR) from {pdf.name}")
    finally:
        store.close()
        conn.close()


if __name__ == "__main__":
    main()
