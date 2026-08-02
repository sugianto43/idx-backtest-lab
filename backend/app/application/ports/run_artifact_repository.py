from typing import Protocol

from app.domain.execution_result import (
    CashEvent,
    ExecutionWarning,
    FillEvent,
    OrderEvent,
    PositionEvent,
)
from app.domain.pagination import Page
from app.domain.run_artifact import (
    MetricRecord,
    PortfolioSnapshot,
    ReproducibilityManifest,
    RunArtifactBundle,
)


class RunArtifactRepository(Protocol):
    def get_bundle(self, run_id: str) -> RunArtifactBundle | None: ...

    def list_order_events(self, run_id: str, *, limit: int, offset: int) -> Page[OrderEvent]: ...

    def list_fill_events(self, run_id: str, *, limit: int, offset: int) -> Page[FillEvent]: ...

    def list_position_events(
        self, run_id: str, *, limit: int, offset: int
    ) -> Page[PositionEvent]: ...

    def list_cash_events(self, run_id: str, *, limit: int, offset: int) -> Page[CashEvent]: ...

    def list_warnings(self, run_id: str, *, limit: int, offset: int) -> Page[ExecutionWarning]: ...

    def list_portfolio_snapshots(
        self, run_id: str, *, limit: int, offset: int
    ) -> Page[PortfolioSnapshot]: ...

    def list_metrics(self, run_id: str) -> list[MetricRecord]: ...

    def get_reproducibility_manifest(self, run_id: str) -> ReproducibilityManifest | None: ...
