"""Shared API dependencies / health checks."""

from __future__ import annotations

from ..config import DATABASE_URL
from ..index.store import _psycopg_dsn


def database_ok() -> bool:
    """True if Postgres answers a trivial query within a short timeout."""
    try:
        import psycopg

        with psycopg.connect(_psycopg_dsn(DATABASE_URL), connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
