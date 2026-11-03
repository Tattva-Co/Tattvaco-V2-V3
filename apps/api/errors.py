"""Map domain errors to HTTP responses in one place.

Response body shape for every handled error: ``{"detail": str, "error": str}`` where
``error`` is the domain error class name (stable, machine-readable).
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from packages.core.logging import get_logger
from packages.domain.errors import (
    DomainInvariantError,
    InvalidStateError,
    NotFoundError,
    PayloadTooLargeError,
    TenantAccessViolation,
    UnsupportedMediaTypeError,
    ValidationFailure,
    VersionConflictError,
)
from packages.services.identity import AuthenticationError

logger = get_logger("api.errors")

# Most specific first: the first matching class wins.
_STATUS_BY_ERROR = (
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (TenantAccessViolation, status.HTTP_403_FORBIDDEN),
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (VersionConflictError, status.HTTP_409_CONFLICT),
    (InvalidStateError, status.HTTP_409_CONFLICT),
    (PayloadTooLargeError, status.HTTP_413_CONTENT_TOO_LARGE),
    (UnsupportedMediaTypeError, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE),
    (ValidationFailure, status.HTTP_422_UNPROCESSABLE_CONTENT),
    (DomainInvariantError, status.HTTP_409_CONFLICT),
)


def status_for(exc: DomainInvariantError) -> int:
    for error_type, code in _STATUS_BY_ERROR:
        if isinstance(exc, error_type):
            return code
    return status.HTTP_409_CONFLICT


async def _domain_error_handler(request: Request, exc: DomainInvariantError) -> JSONResponse:
    code = status_for(exc)
    logger.info("%s %s -> %s %s: %s", request.method, request.url.path, code, type(exc).__name__, exc)
    return JSONResponse(status_code=code, content={"detail": str(exc), "error": type(exc).__name__})


async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "error": "InternalError"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainInvariantError, _domain_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
