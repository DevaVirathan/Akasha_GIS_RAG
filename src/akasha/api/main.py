"""FastAPI app factory: middleware, error handlers, routers."""

from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError

from .errors import (
    ProblemException,
    problem_handler,
    unhandled_handler,
    validation_handler,
)
from .routes import chat, health, search
from .security import require_user


def create_app() -> FastAPI:
    app = FastAPI(title="Akasha GIS RAG API", version="0.1.0")

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        return response

    app.add_exception_handler(ProblemException, problem_handler)
    app.add_exception_handler(RequestValidationError, validation_handler)
    app.add_exception_handler(Exception, unhandled_handler)

    protected = [Depends(require_user)]  # every /api/v1 route needs a @thaarei.com JWT
    app.include_router(health.router)                                            # open: /healthz, /readyz
    app.include_router(search.router, prefix="/api/v1", dependencies=protected)  # /api/v1/search
    app.include_router(chat.router, prefix="/api/v1", dependencies=protected)    # /api/v1/chat
    return app


app = create_app()
