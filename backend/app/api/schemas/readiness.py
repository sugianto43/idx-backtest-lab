from typing import Literal

from pydantic import BaseModel


class ReadinessResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    database: Literal["ready"]
