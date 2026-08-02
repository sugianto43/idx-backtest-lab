from datetime import datetime
from typing import Any

from app.application.errors import (
    BacktestRunNotFoundError,
    InvalidStatusTransitionError,
    StaleRunStatusError,
    UnknownDatasetReferenceError,
)
from app.domain.backtest_run import BacktestRunStatus, RunManifest, is_transition_allowed
from app.domain.pagination import Page
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import from_naive_utc, to_naive_utc
from app.infrastructure.settings import Settings

_COLUMNS = (
    "run_id",
    "dataset_id",
    "strategy_spec_version",
    "engine_version",
    "configuration_json",
    "status",
    "created_at_utc",
    "started_at_utc",
    "finished_at_utc",
    "warning_count",
    "failure_code",
    "schema_version",
    "manifest_checksum",
    "strategy_id",
    "strategy_version",
)


def _row_to_run(row: dict[str, Any]) -> RunManifest:
    return RunManifest(
        run_id=row["run_id"],
        dataset_id=row["dataset_id"],
        strategy_spec_version=row["strategy_spec_version"],
        engine_version=row["engine_version"],
        configuration_json=row["configuration_json"],
        status=BacktestRunStatus(row["status"]),
        created_at_utc=from_naive_utc(row["created_at_utc"]),
        warning_count=row["warning_count"],
        started_at_utc=from_naive_utc(row["started_at_utc"]) if row["started_at_utc"] else None,
        finished_at_utc=from_naive_utc(row["finished_at_utc"]) if row["finished_at_utc"] else None,
        failure_code=row["failure_code"],
        schema_version=row["schema_version"],
        manifest_checksum=row["manifest_checksum"],
        strategy_id=row["strategy_id"],
        strategy_version=row["strategy_version"],
    )


def _run_values(run: RunManifest) -> list[Any]:
    return [
        run.run_id,
        run.dataset_id,
        run.strategy_spec_version,
        run.engine_version,
        run.configuration_json,
        run.status.value,
        to_naive_utc(run.created_at_utc),
        to_naive_utc(run.started_at_utc) if run.started_at_utc else None,
        to_naive_utc(run.finished_at_utc) if run.finished_at_utc else None,
        run.warning_count,
        run.failure_code,
        run.schema_version,
        run.manifest_checksum,
        run.strategy_id,
        run.strategy_version,
    ]


class DuckDBBacktestRunRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create(self, run: RunManifest) -> RunManifest:
        with connect(self._settings) as connection:
            dataset_exists = connection.execute(
                "SELECT 1 FROM datasets WHERE dataset_id = ?", [run.dataset_id]
            ).fetchone()
            if dataset_exists is None:
                raise UnknownDatasetReferenceError(run.dataset_id)

            connection.execute(
                f"""
                INSERT INTO backtest_runs ({", ".join(_COLUMNS)})
                VALUES ({", ".join("?" for _ in _COLUMNS)})
                """,
                _run_values(run),
            )
        return run

    def get(self, run_id: str) -> RunManifest | None:
        with connect(self._settings) as connection:
            row = connection.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM backtest_runs WHERE run_id = ?", [run_id]
            ).fetchone()
        if row is None:
            return None
        return _row_to_run(dict(zip(_COLUMNS, row, strict=True)))

    def list(self, *, limit: int, offset: int) -> Page[RunManifest]:
        with connect(self._settings) as connection:
            total = int(connection.execute("SELECT COUNT(*) FROM backtest_runs").fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT {", ".join(_COLUMNS)} FROM backtest_runs
                ORDER BY created_at_utc, run_id
                LIMIT ? OFFSET ?
                """,
                [limit, offset],
            ).fetchall()
        items = [_row_to_run(dict(zip(_COLUMNS, row, strict=True))) for row in rows]
        return Page(items=items, total=total, limit=limit, offset=offset)

    def transition_status(
        self,
        run_id: str,
        *,
        expected_status: BacktestRunStatus,
        next_status: BacktestRunStatus,
        started_at_utc: datetime | None = None,
        finished_at_utc: datetime | None = None,
        failure_code: str | None = None,
    ) -> RunManifest:
        if not is_transition_allowed(expected_status, next_status):
            raise InvalidStatusTransitionError(expected_status, next_status)

        with connect(self._settings) as connection:
            updated_rows = connection.execute(
                f"""
                UPDATE backtest_runs
                SET status = ?,
                    started_at_utc = COALESCE(?, started_at_utc),
                    finished_at_utc = COALESCE(?, finished_at_utc),
                    failure_code = COALESCE(?, failure_code)
                WHERE run_id = ? AND status = ?
                RETURNING {", ".join(_COLUMNS)}
                """,
                [
                    next_status.value,
                    to_naive_utc(started_at_utc) if started_at_utc else None,
                    to_naive_utc(finished_at_utc) if finished_at_utc else None,
                    failure_code,
                    run_id,
                    expected_status.value,
                ],
            ).fetchall()

            if updated_rows:
                return _row_to_run(dict(zip(_COLUMNS, updated_rows[0], strict=True)))

            current_row = connection.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM backtest_runs WHERE run_id = ?", [run_id]
            ).fetchone()

        if current_row is None:
            raise BacktestRunNotFoundError(run_id)

        current_run = _row_to_run(dict(zip(_COLUMNS, current_row, strict=True)))
        raise StaleRunStatusError(run_id, expected_status, current_run.status)
