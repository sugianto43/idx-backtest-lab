from fastapi import APIRouter, Depends

from app.api.schemas.health import SERVICE_NAME, LivenessResponse, VersionedHealthResponse
from app.infrastructure.settings import Settings, get_settings

liveness_router = APIRouter()


@liveness_router.get("/health", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


v1_router = APIRouter(prefix="/api/v1")


@v1_router.get("/health", response_model=VersionedHealthResponse)
def versioned_readiness_boundary(
    settings: Settings = Depends(get_settings),
) -> VersionedHealthResponse:
    return VersionedHealthResponse(status="ok", service=SERVICE_NAME, version=settings.version)
