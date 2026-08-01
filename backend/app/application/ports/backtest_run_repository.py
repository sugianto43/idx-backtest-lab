from datetime import datetime
from typing import Protocol

from app.domain.backtest_run import BacktestRunStatus, RunManifest
from app.domain.pagination import Page


class BacktestRunRepository(Protocol):
    def create(self, run: RunManifest) -> RunManifest: ...

    def get(self, run_id: str) -> RunManifest | None: ...

    def list(self, *, limit: int, offset: int) -> Page[RunManifest]: ...

    def transition_status(
        self,
        run_id: str,
        *,
        expected_status: BacktestRunStatus,
        next_status: BacktestRunStatus,
        started_at_utc: datetime | None = None,
        finished_at_utc: datetime | None = None,
        failure_code: str | None = None,
    ) -> RunManifest: ...
