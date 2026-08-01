from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.middleware import CorrelationIdMiddleware
from app.api.routes.health import liveness_router, v1_router
from app.infrastructure.logging import configure_logging
from app.infrastructure.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    application = FastAPI(title="idx-backtesting-lab-api", version=settings.version)
    application.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(application)
    application.include_router(liveness_router)
    application.include_router(v1_router)

    return application


app = create_app()
