"""Mint a dev JWT for local API testing (HS256, 24h expiry).

Usage:
    python scripts/dev_token.py                         # devavirathan@thaarei.com
    python scripts/dev_token.py alice@thaarei.com
    python scripts/dev_token.py bob@thaarei.com --admin # marks token is_admin claim
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import jwt  # noqa: E402

from akasha.config import JWT_SECRET  # noqa: E402

email = next((a for a in sys.argv[1:] if not a.startswith("-")), "devavirathan@thaarei.com")
is_admin = "--admin" in sys.argv

token = jwt.encode(
    {"email": email, "is_admin": is_admin, "exp": int(time.time()) + 86400},
    JWT_SECRET,
    algorithm="HS256",
)
print(token)
