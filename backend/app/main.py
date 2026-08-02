import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.middleware import CorrelationIdMiddleware
from app.api.routes.backtest_runs import v1_backtest_runs_router
from app.api.routes.datasets import v1_datasets_router
from app.api.routes.health import liveness_router, v1_router
from app.api.routes.instruments import v1_instruments_router
from app.api.routes.optimizations import v1_optimizations_router
from app.api.routes.readiness import v1_readiness_router
from app.api.routes.run_artifacts import v1_run_artifacts_router
from app.api.routes.strategies import v1_strategies_router
from app.infrastructure.db.connection import connect
from app.infrastructure.db.migration_runner import MigrationError, run_migrations
from app.infrastructure.logging import configure_logging
from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    try:
        with connect(settings) as connection:
            run_migrations(connection)
    except MigrationError:
        logger.exception(
            "Startup database migration failed; readiness checks will report unavailable"
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    application = FastAPI(
        title="idx-backtesting-lab-api", version=settings.version, lifespan=_lifespan
    )
    application.add_middleware(CorrelationIdMiddleware)
    # Local-only, single-user, no-auth tool (see RELEASE_NOTES.md) -- there is no
    # session/cookie-based auth to protect, so a wildcard origin is appropriate.
    # allow_credentials must stay False when allow_origins is "*" (CORS spec).
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-Id"],
    )
    register_exception_handlers(application)
    application.include_router(liveness_router)
    application.include_router(v1_router)
    application.include_router(v1_readiness_router)
    application.include_router(v1_datasets_router)
    application.include_router(v1_instruments_router)
    application.include_router(v1_strategies_router)
    application.include_router(v1_backtest_runs_router)
    application.include_router(v1_run_artifacts_router)
    application.include_router(v1_optimizations_router)

    return application


app = create_app()
