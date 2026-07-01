"""Stage 1 — extract text from PDFs, with OCR fallback for scanned pages.

Strategy (text-first, OCR fallback):
  1. Try native text extraction per page (fast; works on digital PDFs).
  2. If a page yields little/no text, rasterize it and run OCR.

Several books in Data/ are large scans, so the OCR path is expected to fire
often for those. Keep extraction resumable via the on-disk cache.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..config import DATA_DIR
from ..types import PdfPage

# Below this many extracted characters, treat a page as "no text layer" and OCR it.
MIN_CHARS_FOR_TEXT_LAYER = 40


def iter_pdfs(data_dir: Path = DATA_DIR) -> Iterator[Path]:
    """Yield every .pdf under data_dir (recursively). Implemented — used by
    scripts to discover the corpus."""
    yield from sorted(data_dir.rglob("*.pdf"))


def extract_pdf(pdf_path: Path) -> list[PdfPage]:
    """Return one PdfPage per page, using the text-first / OCR-fallback strategy.

    TODO: open with PyMuPDF, read page.get_text(); if len(text) <
    MIN_CHARS_FOR_TEXT_LAYER call ocr_page(); set folder from pdf_path.parent.name.
    """
    raise NotImplementedError


def ocr_page(pdf_path: Path, page_number: int) -> str:
    """Rasterize one page (PyMuPDF pixmap) and OCR it (pytesseract).

    Requires the Tesseract binary to be installed on the system.
    """
    raise NotImplementedError
