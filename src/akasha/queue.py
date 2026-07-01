"""Minimal Redis-backed job queue (a list + BLPOP). Lazy imports.

Kept intentionally simple and fork-free so it runs identically on Windows.
Swap for RQ/Celery later without changing callers.
"""

from __future__ import annotations

import json

from .config import REDIS_URL

_QUEUE_KEY = "akasha:ingest"


def _redis():
    import redis

    return redis.Redis.from_url(REDIS_URL)


def enqueue(job: dict) -> None:
    _redis().rpush(_QUEUE_KEY, json.dumps(job))


def dequeue(timeout: int = 10) -> dict | None:
    """Block up to `timeout`s for one job; return it, or None if none arrived."""
    import redis

    try:
        item = _redis().blpop(_QUEUE_KEY, timeout=timeout)
    except redis.exceptions.TimeoutError:
        return None
    return json.loads(item[1]) if item else None
