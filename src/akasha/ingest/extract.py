"""Stage 1 — extract text from PDFs (path or bytes), OCR fallback for scans.

Text-first: try native extraction; if a page yields little/no text, rasterize
and OCR it. OCR needs the Tesseract binary; if it's missing, ocr_page returns ""
and the page is stored empty rather than failing the run. fitz (PyMuPDF) is
imported lazily.
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
    """Extract from a PDF on disk."""
    import fitz  # PyMuPDF

    doc = fitz.open(pdf_path)
    return _extract(doc, pdf_path.name, pdf_path.parent.name, max_pages)


def extract_pdf_bytes(
    data: bytes,
    *,
    source_file: str = "upload.pdf",
    folder: str = "upload",
    max_pages: int | None = None,
) -> list[PdfPage]:
    """Extract from PDF bytes (e.g. downloaded from object storage)."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    return _extract(doc, source_file, folder, max_pages)


def _extract(doc, source_file: str, folder: str, max_pages: int | None) -> list[PdfPage]:
    pages: list[PdfPage] = []
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
                    source_file=source_file,
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
    """Rasterize a PyMuPDF page and OCR it. Returns '' if OCR is unavailable."""
    try:
        import io

        import pytesseract
        from PIL import Image

        pix = page.get_pixmap(dpi=200)
        image = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(image).strip()
    except Exception:
        return ""
