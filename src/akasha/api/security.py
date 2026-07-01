"""@thaarei.com JWT auth: mint (dev) + verify (identity gate) + is_admin.

The token proves identity (a verified @thaarei.com email); the DB is the source
of truth for authorization (is_admin, is_active). PyJWT and psycopg are imported
lazily. For local dev, get a token from POST /api/v1/auth/dev-login (guarded by
DEV_AUTH) or scripts/dev_token.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..config import DATABASE_URL, JWT_SECRET
from ..index.store import _psycopg_dsn
from .errors import ProblemException

ALLOWED_DOMAIN = "@thaarei.com"
_UNAUTHORIZED = "https://api.akasha/errors/unauthorized"
_FORBIDDEN = "https://api.akasha/errors/forbidden"

# auto_error=False so missing/blank creds become our Problem-Details 401.
_bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user_id: str
    email: str
    is_admin: bool


def mint_token(email: str, *, is_admin: bool = False, ttl_hours: int = 24) -> str:
    """Sign an HS256 JWT (used by the dev-login endpoint and scripts/dev_token.py)."""
    import jwt

    payload = {"email": email, "is_admin": is_admin, "exp": int(time.time()) + ttl_hours * 3600}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def require_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> Principal:
    if creds is None:
        raise ProblemException(401, "Not authenticated", "Missing bearer token.", _UNAUTHORIZED)

    import jwt

    try:
        claims = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise ProblemException(401, "Invalid token", "Token is invalid or expired.", _UNAUTHORIZED)

    email = str(claims.get("email", "")).lower()
    if not email.endswith(ALLOWED_DOMAIN):
        raise ProblemException(
            403, "Forbidden", "Only @thaarei.com accounts may use this system.", _FORBIDDEN
        )

    principal = provision_user(email)
    if principal is None:
        raise ProblemException(403, "Inactive account", "This account is deactivated.", _FORBIDDEN)
    return principal


def require_admin(principal: Principal = Depends(require_user)) -> Principal:
    if not principal.is_admin:
        raise ProblemException(403, "Admin only", "This action requires an admin.", _FORBIDDEN)
    return principal


def provision_user(email: str) -> Principal | None:
    """JIT-upsert the user and return authorization from the DB (source of truth)."""
    import psycopg

    with psycopg.connect(_psycopg_dsn(DATABASE_URL), connect_timeout=2, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email) VALUES (%s) "
                "ON CONFLICT (email) DO UPDATE SET last_login_at = now() "
                "RETURNING id, is_admin, is_active",
                (email,),
            )
            user_id, is_admin, is_active = cur.fetchone()
    if not is_active:
        return None
    return Principal(user_id=str(user_id), email=email, is_admin=is_admin)
