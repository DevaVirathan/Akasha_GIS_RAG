"""Liveness and readiness endpoints (outside /api/v1)."""

from fastapi import APIRouter, Response

from ..deps import database_ok

router = APIRouter(tags=["ops"])


@router.get("/healthz")
def healthz() -> dict:
    """Liveness: the process is up. No dependency checks."""
    return {"status": "ok"}


@router.get("/readyz")
def readyz(response: Response) -> dict:
    """Readiness: dependencies reachable. 503 if the DB is down."""
    db = database_ok()
    if not db:
        response.status_code = 503
    return {"status": "ready" if db else "unavailable", "checks": {"database": db}}
