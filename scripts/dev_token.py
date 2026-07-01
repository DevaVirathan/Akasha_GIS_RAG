"""Mint a dev JWT for local API testing (HS256, 24h expiry).

Usage:
    python scripts/dev_token.py                         # devavirathan@thaarei.com
    python scripts/dev_token.py alice@thaarei.com
    python scripts/dev_token.py bob@thaarei.com --admin # marks token is_admin claim

Prefer POST /api/v1/auth/dev-login (when DEV_AUTH=true) from the frontend; this
CLI is the fallback / bootstrap.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from akasha.api.security import mint_token  # noqa: E402

email = next((a for a in sys.argv[1:] if not a.startswith("-")), "devavirathan@thaarei.com")
is_admin = "--admin" in sys.argv
print(mint_token(email, is_admin=is_admin))
