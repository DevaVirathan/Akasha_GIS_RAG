"""Central configuration: paths, model names, chunking params, secrets.

Values are read from the environment (via .env when present). Nothing here
performs I/O beyond loading env vars.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    # python-dotenv not installed yet (scaffold). Fall back to real env vars.
    pass

# --- Paths --------------------------------------------------------------
# config.py -> akasha -> src -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "Data"
STORAGE_DIR = PROJECT_ROOT / "storage"
# Cache of extracted/chunked text so ingestion is resumable across runs.
CACHE_DIR = STORAGE_DIR / "cache"

# --- Models (OpenAI) ----------------------------------------------------
# Embeddings. text-embedding-3-large -> 3072 dims; text-embedding-3-small -> 1536.
# Env-overridable so you can swap after confirming OpenAI's current lineup.
EMBED_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
EMBED_DIM = int(os.getenv("EMBED_DIM", "3072"))  # must match EMBED_MODEL's output

# Answer synthesis. Verify the current model id in your OpenAI account before
# locking; a newer/cheaper model may be preferable.
ANSWER_MODEL = os.getenv("OPENAI_RESPONSE_MODEL", "gpt-4o")

# --- Chunking -----------------------------------------------------------
CHUNK_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 120

# --- Retrieval ----------------------------------------------------------
TOP_K = 6

# --- Secrets ------------------------------------------------------------
# Never hardcode the key. Put OPENAI_API_KEY in .env (gitignored) and read it
# at the call site via require("OPENAI_API_KEY").
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def require(name: str) -> str:
    """Return an env var's value or raise if unset. Use at call sites that
    actually need the secret, so import-time never fails."""
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"Environment variable {name} is not set (see .env.example).")
    return value
