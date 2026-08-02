from datetime import datetime
from typing import Protocol

from app.domain.optimization import (
    ObjectiveStatus,
    OptimizationCandidate,
    OptimizationManifest,
    OptimizationStatus,
)
from app.domain.pagination import Page


class OptimizationRepository(Protocol):
    def create(
        self, manifest: OptimizationManifest, candidates: list[OptimizationCandidate]
    ) -> None: ...

    def get(self, optimization_id: str) -> OptimizationManifest | None: ...

    def list(self, *, limit: int, offset: int) -> Page[OptimizationManifest]: ...

    def list_candidates(
        self, optimization_id: str, *, limit: int, offset: int
    ) -> Page[OptimizationCandidate]: ...

    def transition_status(
        self,
        optimization_id: str,
        *,
        expected_status: OptimizationStatus,
        next_status: OptimizationStatus,
        started_at_utc: datetime | None = None,
        finished_at_utc: datetime | None = None,
        failure_code: str | None = None,
    ) -> OptimizationManifest: ...

    def record_candidate_result(
        self,
        candidate_id: str,
        *,
        status: str,
        strategy_id: str | None,
        strategy_version: int | None,
        train_run_id: str | None,
        validation_run_id: str | None,
        objective_status: ObjectiveStatus | None,
        objective_value: str | None,
        objective_reason: str | None,
        warning_count: int,
    ) -> None: ...

    def record_selection(
        self,
        optimization_id: str,
        *,
        selected_candidate_id: str | None,
        selection_reason: str,
        selection_audit_json: str,
        selected_at_utc: datetime,
    ) -> None: ...

    def record_holdout_result(
        self,
        optimization_id: str,
        *,
        holdout_run_id: str,
        holdout_objective_status: ObjectiveStatus,
        holdout_objective_value: str | None,
        holdout_objective_reason: str | None,
    ) -> None: ...
