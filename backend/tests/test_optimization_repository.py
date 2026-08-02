from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import duckdb
import pytest

from app.application.errors import StaleOptimizationStatusError
from app.domain.dataset import DatasetManifest, DatasetValidationStatus
from app.domain.instrument import Instrument, InstrumentStatus, InstrumentType
from app.domain.optimization import (
    CandidateStatus,
    ObjectiveStatus,
    OptimizationCandidate,
    OptimizationManifest,
    OptimizationStatus,
)
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.instrument_repository import DuckDBInstrumentRepository
from app.infrastructure.db.migration_runner import run_migrations
from app.infrastructure.db.optimization_repository import DuckDBOptimizationRepository
from app.infrastructure.settings import Settings

DAY1 = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def settings(tmp_path: Any) -> Settings:
    db_path = tmp_path / "test.duckdb"
    connection = duckdb.connect(str(db_path))
    run_migrations(connection)
    connection.close()
    return Settings(database_path=str(db_path))


@pytest.fixture
def dataset_and_instrument(settings: Settings) -> tuple[str, str]:
    dataset = DatasetManifest(
        dataset_id="ds-1",
        version=1,
        name="Sample dataset",
        source_name="synthetic-test",
        bar_interval="1d",
        timezone="UTC",
        adjustment_policy="unknown",
        validation_status=DatasetValidationStatus.VALID,
        created_at_utc=DAY1,
    )
    DuckDBDatasetRepository(settings).create(dataset)

    instrument = Instrument(
        instrument_id="instr-1",
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        source_name="manual",
        status=InstrumentStatus.UNKNOWN,
        created_at_utc=DAY1,
    )
    DuckDBInstrumentRepository(settings).create(instrument)
    return dataset.dataset_id, instrument.instrument_id


def _manifest(dataset_id: str, instrument_id: str, **overrides: Any) -> OptimizationManifest:
    defaults: dict[str, Any] = dict(
        optimization_id="opt-1",
        schema_version=1,
        checksum="sha256:abc",
        dataset_id=dataset_id,
        instrument_id=instrument_id,
        base_strategy_name="SMA grid",
        fast_window_grid=(2, 3),
        slow_window_grid=(4, 5),
        train_start=date(2026, 1, 1),
        train_end=date(2026, 1, 10),
        validation_start=date(2026, 1, 11),
        validation_end=date(2026, 1, 20),
        holdout_start=date(2026, 1, 21),
        holdout_end=date(2026, 1, 30),
        capital_amount=Decimal("1000000"),
        capital_currency="IDR",
        position_sizing_fraction=Decimal("0.5"),
        quantity_increment=Decimal("1"),
        money_scale=2,
        annualization_basis=252,
        risk_free_rate=Decimal("0"),
        objective_metric_key="total_return",
        tie_break_rule="highest_objective_value",
        max_candidate_count=50,
        candidate_count=4,
        rejected_count=0,
        manifest_json='{"schema_version": 1}',
        status=OptimizationStatus.CREATED,
        created_at_utc=DAY1,
    )
    defaults.update(overrides)
    return OptimizationManifest(**defaults)


def _candidate(optimization_id: str, sequence: int, fast: int, slow: int) -> OptimizationCandidate:
    return OptimizationCandidate(
        candidate_id=f"cand-{sequence}",
        optimization_id=optimization_id,
        sequence=sequence,
        fast_window=fast,
        slow_window=slow,
        status=CandidateStatus.PENDING,
        created_at_utc=DAY1,
    )


def test_create_and_get_round_trips_manifest_and_candidates(
    settings: Settings, dataset_and_instrument: tuple[str, str]
) -> None:
    dataset_id, instrument_id = dataset_and_instrument
    manifest = _manifest(dataset_id, instrument_id)
    candidates = [_candidate("opt-1", 0, 2, 4), _candidate("opt-1", 1, 2, 5)]
    repository = DuckDBOptimizationRepository(settings)

    repository.create(manifest, candidates)

    stored = repository.get("opt-1")
    assert stored is not None
    assert stored.checksum == "sha256:abc"
    assert stored.fast_window_grid == (2, 3)
    assert stored.capital_amount == Decimal("1000000")
    assert stored.status == OptimizationStatus.CREATED

    page = repository.list_candidates("opt-1", limit=20, offset=0)
    assert page.total == 2
    assert [c.sequence for c in page.items] == [0, 1]


def test_get_unknown_optimization_returns_none(settings: Settings) -> None:
    assert DuckDBOptimizationRepository(settings).get("does-not-exist") is None


def test_transition_status_updates_and_rejects_stale_expectation(
    settings: Settings, dataset_and_instrument: tuple[str, str]
) -> None:
    dataset_id, instrument_id = dataset_and_instrument
    repository = DuckDBOptimizationRepository(settings)
    repository.create(_manifest(dataset_id, instrument_id), [])

    updated = repository.transition_status(
        "opt-1",
        expected_status=OptimizationStatus.CREATED,
        next_status=OptimizationStatus.VALIDATING,
        started_at_utc=DAY1,
    )
    assert updated.status == OptimizationStatus.VALIDATING
    assert updated.started_at_utc == DAY1

    with pytest.raises(StaleOptimizationStatusError):
        repository.transition_status(
            "opt-1",
            expected_status=OptimizationStatus.CREATED,
            next_status=OptimizationStatus.VALIDATING,
        )


def test_record_candidate_result_updates_only_targeted_candidate(
    settings: Settings, dataset_and_instrument: tuple[str, str]
) -> None:
    dataset_id, instrument_id = dataset_and_instrument
    repository = DuckDBOptimizationRepository(settings)
    candidates = [_candidate("opt-1", 0, 2, 4), _candidate("opt-1", 1, 2, 5)]
    repository.create(_manifest(dataset_id, instrument_id), candidates)

    repository.record_candidate_result(
        "cand-0",
        status="completed",
        strategy_id="strat-1",
        strategy_version=1,
        train_run_id="run-train-1",
        validation_run_id="run-val-1",
        objective_status=ObjectiveStatus.AVAILABLE,
        objective_value="0.12",
        objective_reason=None,
        warning_count=2,
    )

    page = repository.list_candidates("opt-1", limit=20, offset=0)
    updated = next(c for c in page.items if c.candidate_id == "cand-0")
    untouched = next(c for c in page.items if c.candidate_id == "cand-1")

    assert updated.status == CandidateStatus.COMPLETED
    assert updated.objective_value == Decimal("0.12")
    assert updated.warning_count == 2
    assert untouched.status == CandidateStatus.PENDING


def test_record_selection_and_holdout_result_round_trip(
    settings: Settings, dataset_and_instrument: tuple[str, str]
) -> None:
    dataset_id, instrument_id = dataset_and_instrument
    repository = DuckDBOptimizationRepository(settings)
    repository.create(_manifest(dataset_id, instrument_id), [_candidate("opt-1", 0, 2, 4)])

    repository.record_selection(
        "opt-1",
        selected_candidate_id="cand-0",
        selection_reason="highest total_return",
        selection_audit_json="[]",
        selected_at_utc=DAY1,
    )
    repository.record_holdout_result(
        "opt-1",
        holdout_run_id="run-holdout-1",
        holdout_objective_status=ObjectiveStatus.AVAILABLE,
        holdout_objective_value="0.03",
        holdout_objective_reason=None,
    )

    stored = repository.get("opt-1")
    assert stored is not None
    assert stored.selected_candidate_id == "cand-0"
    assert stored.selection_reason == "highest total_return"
    assert stored.holdout_run_id == "run-holdout-1"
    assert stored.holdout_objective_value == Decimal("0.03")


def test_list_paginates_optimizations(
    settings: Settings, dataset_and_instrument: tuple[str, str]
) -> None:
    dataset_id, instrument_id = dataset_and_instrument
    repository = DuckDBOptimizationRepository(settings)
    repository.create(_manifest(dataset_id, instrument_id, optimization_id="opt-1"), [])
    repository.create(
        _manifest(dataset_id, instrument_id, optimization_id="opt-2", created_at_utc=DAY1), []
    )

    page = repository.list(limit=1, offset=0)

    assert page.total == 2
    assert len(page.items) == 1
