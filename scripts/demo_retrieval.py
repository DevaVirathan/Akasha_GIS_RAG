"""End-to-end demo: embed domain snippets → store → ask a question → cited chunks.

Requires: docker services up, `alembic upgrade head`, and OPENAI_API_KEY in .env.
Run:      python scripts/demo_retrieval.py

Seeds a throwaway published document, retrieves, then deletes it (cascades).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import psycopg  # noqa: E402

from akasha.config import DATABASE_URL  # noqa: E402
from akasha.index.embed import embed_texts  # noqa: E402
from akasha.index.store import VectorStore, _psycopg_dsn  # noqa: E402
from akasha.query.retrieve import retrieve  # noqa: E402
from akasha.types import Chunk  # noqa: E402

SNIPPETS = [
    "NDVI (Normalized Difference Vegetation Index) is computed from the Red and "
    "Near-Infrared (NIR) bands as (NIR - Red) / (NIR + Red); values range -1 to 1.",
    "Synthetic Aperture Radar (SAR) is an active microwave sensor that images the "
    "surface through clouds and at night, unlike optical sensors.",
    "Atmospheric correction removes scattering and absorption by the atmosphere to "
    "recover surface reflectance before computing indices.",
    "NDMI (Normalized Difference Moisture Index) uses NIR and SWIR bands to estimate "
    "vegetation water content.",
]

QUESTION = "Which bands are used to calculate NDVI?"


def main() -> None:
    store = VectorStore()
    conn = psycopg.connect(_psycopg_dsn(DATABASE_URL), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO documents (title, allowed_for_rag, is_active, checksum, file_path) "
            "VALUES ('Demo RS Notes', true, true, %s, 's3://demo') RETURNING id",
            ("demo-" + uuid.uuid4().hex,),
        )
        doc_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO document_versions (document_id, version_no, file_path, checksum, status) "
            "VALUES (%s, 1, 's3://demo', %s, 'published') RETURNING id",
            (doc_id, "demo-" + uuid.uuid4().hex),
        )
        ver_id = cur.fetchone()[0]

    try:
        print(f"Embedding {len(SNIPPETS)} snippets with OpenAI…")
        vectors = embed_texts(SNIPPETS)
        chunks = [
            Chunk(
                document_id=doc_id,
                document_version_id=ver_id,
                chunk_index=i,
                text=text,
                page_start=i + 1,
                section="Demo",
            )
            for i, text in enumerate(SNIPPETS)
        ]
        store.add(chunks, vectors)

        print(f"\nQ: {QUESTION}\n")
        for rank, r in enumerate(retrieve(QUESTION, k=3, store=store), start=1):
            cite = f"{r.chunk.source_title} p.{r.chunk.page_start}"
            print(f"{rank}. score={r.score:.3f}  [{cite}]")
            print(f"   {r.chunk.text[:90]}…\n")
    finally:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))  # cascades
        conn.close()
        store.close()


if __name__ == "__main__":
    main()
