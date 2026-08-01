from typing import Literal

from pydantic import BaseModel

SERVICE_NAME = "idx-backtesting-lab-api"


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class VersionedHealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
