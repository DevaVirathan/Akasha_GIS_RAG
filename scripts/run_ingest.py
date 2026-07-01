"""Ingest the corpus: extract -> chunk -> embed -> store.

Usage (once modules are implemented):
    python scripts/run_ingest.py            # all PDFs under Data/
    python scripts/run_ingest.py --limit 1  # smoke-test on the first PDF

Scaffold: wiring is present but pipeline stages raise NotImplementedError.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make src/ importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from akasha.index.embed import embed_texts  # noqa: E402
from akasha.index.store import VectorStore  # noqa: E402
from akasha.ingest.chunk import chunk_pages  # noqa: E402
from akasha.ingest.extract import extract_pdf, iter_pdfs  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the GIS/RS PDF corpus.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N PDFs.")
    args = parser.parse_args()

    store = VectorStore()
    pdfs = list(iter_pdfs())
    if args.limit is not None:
        pdfs = pdfs[: args.limit]

    for pdf in pdfs:
        print(f"[extract] {pdf.name}")
        pages = extract_pdf(pdf)
        chunks = chunk_pages(pages)
        embeddings = embed_texts([c.text for c in chunks])
        store.add(chunks, embeddings)
        print(f"[stored]  {len(chunks)} chunks from {pdf.name}")


if __name__ == "__main__":
    main()
