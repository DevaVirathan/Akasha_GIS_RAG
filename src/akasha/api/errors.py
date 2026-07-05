"""RFC 9457 Problem Details error model and handlers."""

from __future__ import annotations

import traceback

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ProblemException(Exception):
    """Raise to return an application/problem+json error."""

    def __init__(self, status: int, title: str, detail: str = "", type_: str = "about:blank") -> None:
        self.status = status
        self.title = title
        self.detail = detail
        self.type = type_


def _problem(request: Request, status: int, title: str, detail: str, type_: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": type_,
            "title": title,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def problem_handler(request: Request, exc: ProblemException) -> JSONResponse:
    return _problem(request, exc.status, exc.title, exc.detail, exc.type)


async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _problem(
        request, 422, "Invalid request", str(exc.errors()),
        "https://api.akasha/errors/validation",
    )


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    print(
        f"Unhandled error on {request.url.path} "
        f"rid={getattr(request.state, 'request_id', None)}",
        flush=True,
    )
    traceback.print_exc()
    return _problem(
        request, 500, "Internal server error", "",
        "https://api.akasha/errors/internal",
    )
