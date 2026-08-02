from datetime import datetime
from typing import Any

from pydantic import BaseModel


class MetricSchema(BaseModel):
    metric_key: str
    status: str
    value: str | None
    reason: str | None
    definition_version: int


class RunSummaryResponse(BaseModel):
    run_id: str
    status: str
    terminal_status: str | None
    manifest_checksum: str | None
    artifact_schema_version: int | None
    artifact_checksum: str | None
    event_count: int | None
    snapshot_count: int | None
    warning_count: int
    metrics: list[MetricSchema]


class RunArtifactsResponse(BaseModel):
    bundle_id: str
    run_id: str
    artifact_schema_version: int
    checksum: str
    terminal_status: str
    provenance: dict[str, Any]
    event_count: int
    snapshot_count: int
    metric_count: int
    created_at_utc: datetime
    sections: dict[str, str]


class PaginatedEventsResponse(BaseModel):
    type: str
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class PortfolioSnapshotSchema(BaseModel):
    sequence: int
    timestamp_utc: datetime
    cash: str
    holdings_value: str
    total_equity: str
    currency: str
    status: str
    reason: str | None


class PortfolioSnapshotsResponse(BaseModel):
    items: list[PortfolioSnapshotSchema]
    total: int
    limit: int
    offset: int


class RunMetricsResponse(BaseModel):
    items: list[MetricSchema]


class ReproducibilityManifestResponse(BaseModel):
    filename: str
    content_type: str
    checksum: str
    manifest: dict[str, Any]


class ComparisonCompatibilityResponse(BaseModel):
    compatible: bool
    reasons: list[str]
