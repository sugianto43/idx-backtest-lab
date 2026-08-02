from typing import Protocol

from app.domain.execution_result import (
    CashEvent,
    ExecutionWarning,
    FillEvent,
    OrderEvent,
    PositionEvent,
)
from app.domain.run_artifact import (
    MetricRecord,
    PortfolioSnapshot,
    ReproducibilityManifest,
    RunArtifactBundle,
)


class RunArtifactWriter(Protocol):
    def persist(
        self,
        *,
        bundle: RunArtifactBundle,
        order_events: list[OrderEvent],
        fill_events: list[FillEvent],
        position_events: list[PositionEvent],
        cash_events: list[CashEvent],
        warnings: list[ExecutionWarning],
        snapshots: list[PortfolioSnapshot],
        metrics: list[MetricRecord],
        reproducibility_manifest: ReproducibilityManifest,
    ) -> None: ...
