from fastapi import APIRouter, Depends

from app.api.errors import DependencyUnavailableError
from app.api.schemas.health import SERVICE_NAME
from app.api.schemas.readiness import ReadinessResponse
from app.infrastructure.db.readiness import is_database_ready
from app.infrastructure.settings import Settings, get_settings

v1_readiness_router = APIRouter(prefix="/api/v1")


@v1_readiness_router.get("/ready", response_model=ReadinessResponse)
def ready(settings: Settings = Depends(get_settings)) -> ReadinessResponse:
    if not is_database_ready(settings):
        raise DependencyUnavailableError()
    return ReadinessResponse(
        status="ok", service=SERVICE_NAME, version=settings.version, database="ready"
    )
