"""Request correlation ID middleware (C9).

Every request gets an ID -- the caller's own `X-Request-ID` if it sent one (so a request
that already has an ID upstream, e.g. from a load balancer or another service, keeps it
end to end), otherwise a fresh one. The ID is echoed back in the response header and set
on `packages.core.logging.request_id_var` for the lifetime of the request, so every log
line emitted while handling it carries the same `request_id` with no extra plumbing at
each call site.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from packages.core.logging import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
