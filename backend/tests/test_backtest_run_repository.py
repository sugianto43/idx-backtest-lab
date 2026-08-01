from datetime import UTC, datetime
from typing import Any

import duckdb
import pytest

from app.application.errors import (
    BacktestRunNotFoundError,
    InvalidStatusTransitionError,
    StaleRunStatusError,
    UnknownDatasetReferenceError,
)
from app.domain.backtest_run import BacktestRunStatus, RunManifest, RunManifestValidationError
from app.domain.dataset import DatasetManifest, DatasetValidationStatus
from app.infrastructure.db.backtest_run_repository import DuckDBBacktestRunRepository
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.migration_runner import run_migrations
from app.infrastructure.settings import Settings


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    db_path = tmp_path / "test.duckdb"
    connection = duckdb.connect(str(db_path))
    run_migrations(connection)
    connection.close()
    return Settings(database_path=str(db_path))


@pytest.fixture
def dataset_id(settings: Settings) -> str:
    dataset = DatasetManifest(
        dataset_id="ds-1",
        version=1,
        name="Sample dataset",
        source_name="synthetic-test",
        bar_interval="1d",
        timezone="UTC",
        adjustment_policy="unknown",
        validation_status=DatasetValidationStatus.VALID,
        created_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )
    DuckDBDatasetRepository(settings).create(dataset)
    return dataset.dataset_id


def _manifest(dataset_id: str, **overrides: Any) -> RunManifest:
    defaults: dict[str, Any] = {
        "run_id": "run-1",
        "dataset_id": dataset_id,
        "strategy_spec_version": "sma_crossover@1",
        "engine_version": "backtrader-adapter@0",
        "configuration_json": "{}",
        "status": BacktestRunStatus.CREATED,
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
    }
    defaults.update(overrides)
    return RunManifest(**defaults)


def test_create_and_get_round_trip(settings: Settings, dataset_id: str) -> None:
    repository = DuckDBBacktestRunRepository(settings)
    manifest = _manifest(dataset_id)

    repository.create(manifest)
    fetched = repository.get("run-1")

    assert fetched == manifest


def test_get_returns_none_for_unknown_id(settings: Settings) -> None:
    repository = DuckDBBacktestRunRepository(settings)

    assert repository.get("does-not-exist") is None


def test_create_rejects_unknown_dataset(settings: Settings) -> None:
    repository = DuckDBBacktestRunRepository(settings)
    manifest = _manifest("does-not-exist")

    with pytest.raises(UnknownDatasetReferenceError):
        repository.create(manifest)


def test_transition_status_success(settings: Settings, dataset_id: str) -> None:
    repository = DuckDBBacktestRunRepository(settings)
    repository.create(_manifest(dataset_id))

    updated = repository.transition_status(
        "run-1",
        expected_status=BacktestRunStatus.CREATED,
        next_status=BacktestRunStatus.RUNNING,
        started_at_utc=datetime(2026, 1, 1, 1, tzinfo=UTC),
    )

    assert updated.status == BacktestRunStatus.RUNNING
    assert updated.started_at_utc == datetime(2026, 1, 1, 1, tzinfo=UTC)


def test_transition_status_rejects_disallowed_transition(
    settings: Settings, dataset_id: str
) -> None:
    repository = DuckDBBacktestRunRepository(settings)
    repository.create(_manifest(dataset_id))

    with pytest.raises(InvalidStatusTransitionError):
        repository.transition_status(
            "run-1",
            expected_status=BacktestRunStatus.CREATED,
            next_status=BacktestRunStatus.COMPLETED,
        )


def test_transition_status_rejects_stale_expected_status(
    settings: Settings, dataset_id: str
) -> None:
    repository = DuckDBBacktestRunRepository(settings)
    repository.create(_manifest(dataset_id))
    repository.transition_status(
        "run-1",
        expected_status=BacktestRunStatus.CREATED,
        next_status=BacktestRunStatus.RUNNING,
    )

    with pytest.raises(StaleRunStatusError):
        repository.transition_status(
            "run-1",
            expected_status=BacktestRunStatus.CREATED,
            next_status=BacktestRunStatus.CANCELLED,
        )


def test_transition_status_rejects_unknown_run(settings: Settings) -> None:
    repository = DuckDBBacktestRunRepository(settings)

    with pytest.raises(BacktestRunNotFoundError):
        repository.transition_status(
            "does-not-exist",
            expected_status=BacktestRunStatus.CREATED,
            next_status=BacktestRunStatus.RUNNING,
        )


def test_domain_rejects_negative_warning_count(dataset_id: str) -> None:
    with pytest.raises(RunManifestValidationError):
        _manifest(dataset_id, warning_count=-1)


def test_domain_rejects_invalid_configuration_json(dataset_id: str) -> None:
    with pytest.raises(RunManifestValidationError):
        _manifest(dataset_id, configuration_json="not-json")


def test_domain_rejects_invalid_status(dataset_id: str) -> None:
    with pytest.raises(RunManifestValidationError):
        _manifest(dataset_id, status="not-a-status")
