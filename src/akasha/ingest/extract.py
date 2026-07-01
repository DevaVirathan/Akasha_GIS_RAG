"""Stage 1 — extract text from PDFs, with OCR fallback for scanned pages.

Strategy (text-first, OCR fallback):
  1. Try native text extraction per page (fast; works on digital PDFs).
  2. If a page yields little/no text, rasterize it and OCR it.

OCR needs the Tesseract binary on the system; if it's missing, ocr_page returns
"" and the page is stored empty rather than failing the whole run. fitz
(PyMuPDF) is imported lazily so importing this module doesn't require it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from ..config import DATA_DIR
from ..types import PdfPage

# Below this many extracted characters, treat a page as "no text layer" and OCR it.
MIN_CHARS_FOR_TEXT_LAYER = 40


def iter_pdfs(data_dir: Path = DATA_DIR) -> Iterator[Path]:
    """Yield every .pdf under data_dir (recursively), sorted."""
    yield from sorted(data_dir.rglob("*.pdf"))


def extract_pdf(pdf_path: Path, max_pages: int | None = None) -> list[PdfPage]:
    """Return one PdfPage per page (text-first, OCR fallback)."""
    import fitz  # PyMuPDF

    folder = pdf_path.parent.name
    pages: list[PdfPage] = []
    doc = fitz.open(pdf_path)
    try:
        for i, page in enumerate(doc):
            if max_pages is not None and i >= max_pages:
                break
            text = page.get_text("text").strip()
            is_ocr = False
            if len(text) < MIN_CHARS_FOR_TEXT_LAYER:
                ocr_text = ocr_page(page)
                if ocr_text:
                    text, is_ocr = ocr_text, True
            pages.append(
                PdfPage(
                    source_file=pdf_path.name,
                    folder=folder,
                    page_number=i + 1,
                    text=text,
                    is_ocr=is_ocr,
                )
            )
    finally:
        doc.close()
    return pages


def ocr_page(page) -> str:
    """Rasterize a PyMuPDF page and OCR it. Returns '' if OCR is unavailable
    (Tesseract/pytesseract/Pillow missing), so ingestion degrades gracefully."""
    try:
        import io

        import pytesseract
        from PIL import Image

        pix = page.get_pixmap(dpi=200)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""
