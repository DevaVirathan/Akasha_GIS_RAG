"""Smoke tests: the scaffold imports and wires together.

These assert structure only — not behavior — since pipeline stages are stubs.
Run with: pytest
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_package_imports():
    import akasha  # noqa: F401
    from akasha import config, types  # noqa: F401
    from akasha.ingest import chunk, extract  # noqa: F401
    from akasha.index import embed, store  # noqa: F401
    from akasha.query import answer, retrieve  # noqa: F401


def test_config_paths_resolve():
    from akasha import config

    assert config.DATA_DIR.name == "Data"
    assert config.PROJECT_ROOT.exists()


def test_iter_pdfs_finds_corpus():
    from akasha.ingest.extract import iter_pdfs

    # The corpus should be discoverable if Data/ is present.
    pdfs = list(iter_pdfs())
    assert all(p.suffix == ".pdf" for p in pdfs)
