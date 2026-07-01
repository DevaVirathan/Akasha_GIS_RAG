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
# Embeddings. Default to 1536 dims because pgvector's HNSW/IVFFlat indexes cap
# at 2000 dims (text-embedding-3-large's native 3072 is NOT ANN-indexable).
# Use text-embedding-3-small (native 1536), OR 3-large with dimensions=1536.
# EMBED_DIM must equal the VECTOR(n) column — lock it before the first migration.
EMBED_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBED_DIM = int(os.getenv("EMBED_DIM", "1536"))  # must match EMBED_MODEL's output

# Answer synthesis. Verify the current model id in your OpenAI account before
# locking; a newer/cheaper model may be preferable.
ANSWER_MODEL = os.getenv("OPENAI_RESPONSE_MODEL", "gpt-4o")

# --- Chunking -----------------------------------------------------------
CHUNK_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 120

# --- Retrieval ----------------------------------------------------------
TOP_K = 6

# --- Infrastructure (local dev via docker-compose.yml) ------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://akasha:akasha@localhost:5432/akasha_rag"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Object storage (S3-compatible; MinIO in local dev)
S3_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
S3_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
S3_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
S3_BUCKET = os.getenv("MINIO_BUCKET", "akasha-documents")

# --- Secrets ------------------------------------------------------------
# Never hardcode the key. Put OPENAI_API_KEY in .env (gitignored) and read it
# at the call site via require("OPENAI_API_KEY").
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# HS256 secret for signing/verifying dev JWTs (override in .env for anything real).
JWT_SECRET = os.getenv("JWT_SECRET", "akasha-local-dev-secret-do-not-use-in-production")

# Dev-only login endpoint (issues JWTs without real auth) — MUST stay false in prod.
DEV_AUTH = os.getenv("DEV_AUTH", "false").lower() in ("1", "true", "yes")

# Browser origins allowed to call the API (the frontend dev server).
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]


def require(name: str) -> str:
    """Return an env var's value or raise if unset. Use at call sites that
    actually need the secret, so import-time never fails."""
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"Environment variable {name} is not set (see .env.example).")
    return value
