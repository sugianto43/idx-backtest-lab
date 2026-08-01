from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.correlation import generate_correlation_id, set_correlation_id

CORRELATION_ID_HEADER = "X-Correlation-Id"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get(CORRELATION_ID_HEADER, "").strip()
        correlation_id = incoming if incoming else generate_correlation_id()
        set_correlation_id(correlation_id)

        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
