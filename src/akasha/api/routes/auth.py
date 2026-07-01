"""Auth endpoints: dev-login (guarded) and identity (/me).

dev-login issues a JWT for a @thaarei.com email WITHOUT real authentication, so
it is disabled unless DEV_AUTH is set (returns 404). In production the external
OIDC IdP issues tokens instead; this endpoint stays off.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...config import DEV_AUTH
from ..errors import ProblemException
from ..schemas import DevLoginRequest, MeResponse, TokenResponse
from ..security import ALLOWED_DOMAIN, Principal, mint_token, provision_user, require_user

router = APIRouter(tags=["auth"])

_FORBIDDEN = "https://api.akasha/errors/forbidden"


@router.post("/auth/dev-login", response_model=TokenResponse)
def dev_login(req: DevLoginRequest) -> TokenResponse:
    if not DEV_AUTH:
        raise ProblemException(
            404, "Not found", "Dev login is disabled.", "https://api.akasha/errors/not-found"
        )
    email = req.email.strip().lower()
    if not email.endswith(ALLOWED_DOMAIN):
        raise ProblemException(403, "Forbidden", "Only @thaarei.com emails are allowed.", _FORBIDDEN)
    principal = provision_user(email)
    if principal is None:
        raise ProblemException(403, "Inactive account", "This account is deactivated.", _FORBIDDEN)
    token = mint_token(email, is_admin=principal.is_admin)
    return TokenResponse(access_token=token, email=email, is_admin=principal.is_admin)


@router.get("/me", response_model=MeResponse)
def me(principal: Principal = Depends(require_user)) -> MeResponse:
    return MeResponse(user_id=principal.user_id, email=principal.email, is_admin=principal.is_admin)
