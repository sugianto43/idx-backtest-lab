import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.infrastructure.correlation import get_correlation_id

logger = logging.getLogger(__name__)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[Any] = []
    correlation_id: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppError(Exception):
    code = "internal_error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "An unexpected error occurred."

    def __init__(self, message: str | None = None, details: list[Any] | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details or []


class NotFoundError(AppError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "The requested resource was not found."


class DependencyUnavailableError(AppError):
    code = "dependency_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "A required dependency is not ready."


def _error_response(status_code: int, code: str, message: str, details: list[Any]) -> JSONResponse:
    correlation_id = get_correlation_id() or "-"
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details, correlation_id=correlation_id)
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return _error_response(
                status.HTTP_404_NOT_FOUND,
                "not_found",
                "The requested resource was not found.",
                [],
            )
        return _error_response(exc.status_code, "http_error", str(exc.detail), [])

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = [{"loc": list(error["loc"]), "message": error["msg"]} for error in exc.errors()]
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "validation_error",
            "Request validation failed.",
            details,
        )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
            [],
        )
