"""FastAPI app factory: middleware, error handlers, routers."""

from __future__ import annotations

import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from ..config import CORS_ORIGINS

from .errors import (
    ProblemException,
    problem_handler,
    unhandled_handler,
    validation_handler,
)
from .routes import auth, chat, documents, health, search
from .security import require_user

def create_app() -> FastAPI:
    app = FastAPI(title="Akasha GIS RAG API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        request.state.request_id = rid
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-Id"] = rid
        print(
            f"{request.method:<6} {request.url.path:<42} -> "
            f"{response.status_code}  {elapsed_ms:>4}ms  rid={rid}",
            flush=True,
        )
        return response

    app.add_exception_handler(ProblemException, problem_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(Exception, unhandled_handler)

    protected = [Depends(require_user)]  # every /api/v1 route needs a @thaarei.com JWT
    app.include_router(health.router)                                            # open: /healthz, /readyz
    app.include_router(search.router, prefix="/api/v1", dependencies=protected)  # /api/v1/search
    app.include_router(chat.router, prefix="/api/v1", dependencies=protected)    # /api/v1/chat
    # documents endpoints declare require_admin per-route (returns the principal)
    app.include_router(documents.router, prefix="/api/v1")                        # /api/v1/documents*
    app.include_router(auth.router, prefix="/api/v1")                             # /api/v1/auth/dev-login, /me
    return app


app = create_app()
