import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.application.errors import (
    OptimizationInvalidTransitionError,
    OptimizationNotFoundError,
    StaleOptimizationStatusError,
)
from app.domain.optimization import (
    CandidateStatus,
    ObjectiveStatus,
    OptimizationCandidate,
    OptimizationManifest,
    OptimizationStatus,
    is_transition_allowed,
)
from app.domain.pagination import Page
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc
from app.infrastructure.settings import Settings

_OPTIMIZATION_COLUMNS = (
    "optimization_id",
    "schema_version",
    "checksum",
    "dataset_id",
    "instrument_id",
    "base_strategy_name",
    "fast_window_grid",
    "slow_window_grid",
    "train_start",
    "train_end",
    "validation_start",
    "validation_end",
    "holdout_start",
    "holdout_end",
    "capital_amount",
    "capital_currency",
    "position_sizing_fraction",
    "quantity_increment",
    "money_scale",
    "annualization_basis",
    "risk_free_rate",
    "objective_metric_key",
    "tie_break_rule",
    "max_candidate_count",
    "candidate_count",
    "rejected_count",
    "manifest_json",
    "status",
    "failure_code",
    "selected_candidate_id",
    "selection_reason",
    "selection_audit_json",
    "selected_at_utc",
    "holdout_run_id",
    "holdout_objective_status",
    "holdout_objective_value",
    "holdout_objective_reason",
    "created_at_utc",
    "started_at_utc",
    "finished_at_utc",
)

_CANDIDATE_COLUMNS = (
    "candidate_id",
    "optimization_id",
    "sequence",
    "fast_window",
    "slow_window",
    "status",
    "rejection_reason",
    "strategy_id",
    "strategy_version",
    "train_run_id",
    "validation_run_id",
    "objective_status",
    "objective_value",
    "objective_reason",
    "warning_count",
    "created_at_utc",
)


def _row_to_manifest(row: dict[str, Any]) -> OptimizationManifest:
    return OptimizationManifest(
        optimization_id=row["optimization_id"],
        schema_version=row["schema_version"],
        checksum=row["checksum"],
        dataset_id=row["dataset_id"],
        instrument_id=row["instrument_id"],
        base_strategy_name=row["base_strategy_name"],
        fast_window_grid=tuple(json.loads(row["fast_window_grid"])),
        slow_window_grid=tuple(json.loads(row["slow_window_grid"])),
        train_start=row["train_start"],
        train_end=row["train_end"],
        validation_start=row["validation_start"],
        validation_end=row["validation_end"],
        holdout_start=row["holdout_start"],
        holdout_end=row["holdout_end"],
        capital_amount=row["capital_amount"],
        capital_currency=row["capital_currency"],
        position_sizing_fraction=row["position_sizing_fraction"],
        quantity_increment=row["quantity_increment"],
        money_scale=row["money_scale"],
        annualization_basis=row["annualization_basis"],
        risk_free_rate=row["risk_free_rate"],
        objective_metric_key=row["objective_metric_key"],
        tie_break_rule=row["tie_break_rule"],
        max_candidate_count=row["max_candidate_count"],
        candidate_count=row["candidate_count"],
        rejected_count=row["rejected_count"],
        manifest_json=row["manifest_json"],
        status=OptimizationStatus(row["status"]),
        failure_code=row["failure_code"],
        selected_candidate_id=row["selected_candidate_id"],
        selection_reason=row["selection_reason"],
        selection_audit_json=row["selection_audit_json"],
        selected_at_utc=from_naive_utc(row["selected_at_utc"]) if row["selected_at_utc"] else None,
        holdout_run_id=row["holdout_run_id"],
        holdout_objective_status=(
            ObjectiveStatus(row["holdout_objective_status"])
            if row["holdout_objective_status"]
            else None
        ),
        holdout_objective_value=(
            Decimal(row["holdout_objective_value"])
            if row["holdout_objective_value"] is not None
            else None
        ),
        holdout_objective_reason=row["holdout_objective_reason"],
        created_at_utc=from_naive_utc(row["created_at_utc"]),
        started_at_utc=from_naive_utc(row["started_at_utc"]) if row["started_at_utc"] else None,
        finished_at_utc=from_naive_utc(row["finished_at_utc"]) if row["finished_at_utc"] else None,
    )


def _row_to_candidate(row: dict[str, Any]) -> OptimizationCandidate:
    return OptimizationCandidate(
        candidate_id=row["candidate_id"],
        optimization_id=row["optimization_id"],
        sequence=row["sequence"],
        fast_window=row["fast_window"],
        slow_window=row["slow_window"],
        status=CandidateStatus(row["status"]),
        created_at_utc=from_naive_utc(row["created_at_utc"]),
        rejection_reason=row["rejection_reason"],
        strategy_id=row["strategy_id"],
        strategy_version=row["strategy_version"],
        train_run_id=row["train_run_id"],
        validation_run_id=row["validation_run_id"],
        objective_status=(
            ObjectiveStatus(row["objective_status"]) if row["objective_status"] else None
        ),
        objective_value=(
            Decimal(row["objective_value"]) if row["objective_value"] is not None else None
        ),
        objective_reason=row["objective_reason"],
        warning_count=row["warning_count"],
    )


def _manifest_values(manifest: OptimizationManifest) -> list[Any]:
    return [
        manifest.optimization_id,
        manifest.schema_version,
        manifest.checksum,
        manifest.dataset_id,
        manifest.instrument_id,
        manifest.base_strategy_name,
        json.dumps(list(manifest.fast_window_grid)),
        json.dumps(list(manifest.slow_window_grid)),
        manifest.train_start,
        manifest.train_end,
        manifest.validation_start,
        manifest.validation_end,
        manifest.holdout_start,
        manifest.holdout_end,
        manifest.capital_amount,
        manifest.capital_currency,
        manifest.position_sizing_fraction,
        manifest.quantity_increment,
        manifest.money_scale,
        manifest.annualization_basis,
        manifest.risk_free_rate,
        manifest.objective_metric_key,
        manifest.tie_break_rule,
        manifest.max_candidate_count,
        manifest.candidate_count,
        manifest.rejected_count,
        manifest.manifest_json,
        manifest.status.value,
        manifest.failure_code,
        manifest.selected_candidate_id,
        manifest.selection_reason,
        manifest.selection_audit_json,
        to_naive_utc(manifest.selected_at_utc) if manifest.selected_at_utc else None,
        manifest.holdout_run_id,
        manifest.holdout_objective_status.value if manifest.holdout_objective_status else None,
        str(manifest.holdout_objective_value)
        if manifest.holdout_objective_value is not None
        else None,
        manifest.holdout_objective_reason,
        to_naive_utc(manifest.created_at_utc),
        to_naive_utc(manifest.started_at_utc) if manifest.started_at_utc else None,
        to_naive_utc(manifest.finished_at_utc) if manifest.finished_at_utc else None,
    ]


def _candidate_values(candidate: OptimizationCandidate) -> list[Any]:
    return [
        candidate.candidate_id,
        candidate.optimization_id,
        candidate.sequence,
        candidate.fast_window,
        candidate.slow_window,
        candidate.status.value,
        candidate.rejection_reason,
        candidate.strategy_id,
        candidate.strategy_version,
        candidate.train_run_id,
        candidate.validation_run_id,
        candidate.objective_status.value if candidate.objective_status else None,
        str(candidate.objective_value) if candidate.objective_value is not None else None,
        candidate.objective_reason,
        candidate.warning_count,
        to_naive_utc(candidate.created_at_utc),
    ]


class DuckDBOptimizationRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(
        self, manifest: OptimizationManifest, candidates: list[OptimizationCandidate]
    ) -> None:
        with connect(self._settings) as connection:
            try:
                connection.execute("BEGIN TRANSACTION")
                connection.execute(
                    f"INSERT INTO optimizations ({', '.join(_OPTIMIZATION_COLUMNS)}) "
                    f"VALUES ({', '.join('?' for _ in _OPTIMIZATION_COLUMNS)})",
                    _manifest_values(manifest),
                )
                if candidates:
                    connection.executemany(
                        f"INSERT INTO optimization_candidates ({', '.join(_CANDIDATE_COLUMNS)}) "
                        f"VALUES ({', '.join('?' for _ in _CANDIDATE_COLUMNS)})",
                        [_candidate_values(candidate) for candidate in candidates],
                    )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def get(self, optimization_id: str) -> OptimizationManifest | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_OPTIMIZATION_COLUMNS)} FROM optimizations "
                "WHERE optimization_id = ?",
                [optimization_id],
            ).fetchone()
        if row is None:
            return None
        return _row_to_manifest(dict(zip(_OPTIMIZATION_COLUMNS, row, strict=True)))

    def list(self, *, limit: int, offset: int) -> Page[OptimizationManifest]:
        with connect(self._settings) as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM optimizations").fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT {", ".join(_OPTIMIZATION_COLUMNS)} FROM optimizations
                ORDER BY created_at_utc, optimization_id
                LIMIT ? OFFSET ?
                """,
                [limit, offset],
            ).fetchall()
        items = [
            _row_to_manifest(dict(zip(_OPTIMIZATION_COLUMNS, row, strict=True))) for row in rows
        ]
        return Page(items=items, total=total, limit=limit, offset=offset)

    def list_candidates(
        self, optimization_id: str, *, limit: int, offset: int
    ) -> Page[OptimizationCandidate]:
        with connect(self._settings) as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM optimization_candidates WHERE optimization_id = ?",
                    [optimization_id],
                ).fetchone()[0]
            )
            rows = connection.execute(
                f"""
                SELECT {", ".join(_CANDIDATE_COLUMNS)} FROM optimization_candidates
                WHERE optimization_id = ?
                ORDER BY sequence
                LIMIT ? OFFSET ?
                """,
                [optimization_id, limit, offset],
            ).fetchall()
        items = [_row_to_candidate(dict(zip(_CANDIDATE_COLUMNS, row, strict=True))) for row in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)

    def transition_status(
        self,
        optimization_id: str,
        *,
        expected_status: OptimizationStatus,
        next_status: OptimizationStatus,
        started_at_utc: datetime | None = None,
        finished_at_utc: datetime | None = None,
        failure_code: str | None = None,
    ) -> OptimizationManifest:
        if not is_transition_allowed(expected_status, next_status):
            raise OptimizationInvalidTransitionError(expected_status.value, next_status.value)

        with connect(self._settings) as connection:
            updated_rows = connection.execute(
                f"""
                UPDATE optimizations
                SET status = ?,
                    started_at_utc = COALESCE(?, started_at_utc),
                    finished_at_utc = COALESCE(?, finished_at_utc),
                    failure_code = COALESCE(?, failure_code)
                WHERE optimization_id = ? AND status = ?
                RETURNING {", ".join(_OPTIMIZATION_COLUMNS)}
                """,
                [
                    next_status.value,
                    to_naive_utc(started_at_utc) if started_at_utc else None,
                    to_naive_utc(finished_at_utc) if finished_at_utc else None,
                    failure_code,
                    optimization_id,
                    expected_status.value,
                ],
            ).fetchall()

            if updated_rows:
                return _row_to_manifest(
                    dict(zip(_OPTIMIZATION_COLUMNS, updated_rows[0], strict=True))
                )

            current_row = connection.execute(
                f"SELECT {', '.join(_OPTIMIZATION_COLUMNS)} FROM optimizations "
                "WHERE optimization_id = ?",
                [optimization_id],
            ).fetchone()

        if current_row is None:
            raise OptimizationNotFoundError(optimization_id)

        current = _row_to_manifest(dict(zip(_OPTIMIZATION_COLUMNS, current_row, strict=True)))
        raise StaleOptimizationStatusError(
            optimization_id, expected_status.value, current.status.value
        )

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
    ) -> None:
        with connect(self._settings) as connection:
            connection.execute(
                """
                UPDATE optimization_candidates
                SET status = ?, strategy_id = ?, strategy_version = ?, train_run_id = ?,
                    validation_run_id = ?, objective_status = ?, objective_value = ?,
                    objective_reason = ?, warning_count = ?
                WHERE candidate_id = ?
                """,
                [
                    status,
                    strategy_id,
                    strategy_version,
                    train_run_id,
                    validation_run_id,
                    objective_status.value if objective_status else None,
                    objective_value,
                    objective_reason,
                    warning_count,
                    candidate_id,
                ],
            )

    def record_selection(
        self,
        optimization_id: str,
        *,
        selected_candidate_id: str | None,
        selection_reason: str,
        selection_audit_json: str,
        selected_at_utc: datetime,
    ) -> None:
        with connect(self._settings) as connection:
            connection.execute(
                """
                UPDATE optimizations
                SET selected_candidate_id = ?, selection_reason = ?, selection_audit_json = ?,
                    selected_at_utc = ?
                WHERE optimization_id = ?
                """,
                [
                    selected_candidate_id,
                    selection_reason,
                    selection_audit_json,
                    to_naive_utc(selected_at_utc),
                    optimization_id,
                ],
            )

    def record_holdout_result(
        self,
        optimization_id: str,
        *,
        holdout_run_id: str,
        holdout_objective_status: ObjectiveStatus,
        holdout_objective_value: str | None,
        holdout_objective_reason: str | None,
    ) -> None:
        with connect(self._settings) as connection:
            connection.execute(
                """
                UPDATE optimizations
                SET holdout_run_id = ?, holdout_objective_status = ?, holdout_objective_value = ?,
                    holdout_objective_reason = ?
                WHERE optimization_id = ?
                """,
                [
                    holdout_run_id,
                    holdout_objective_status.value,
                    holdout_objective_value,
                    holdout_objective_reason,
                    optimization_id,
                ],
            )
