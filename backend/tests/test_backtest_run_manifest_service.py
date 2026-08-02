from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.application.backtest_run_manifest_service import (
    CreateRunManifestRequest,
    DecimalFieldError,
    create_run_manifest,
)
from app.application.errors import (
    DatasetNotFoundError,
    InstrumentNotFoundError,
    StrategySpecNotFoundError,
)
from app.domain.backtest_manifest import RunManifestValidationError
from app.domain.backtest_run import BacktestRunStatus, RunManifest
from app.domain.dataset import DatasetManifest, DatasetValidationStatus, InstrumentMappingPolicy
from app.domain.instrument import Instrument, InstrumentStatus, InstrumentType
from app.domain.pagination import Page
from app.domain.strategy_spec import SignalPolicy, SmaCrossoverParameters, StrategySpecV1


class FakeRunRepository:
    def __init__(self) -> None:
        self.created: list[RunManifest] = []

    def create(self, run: RunManifest) -> RunManifest:
        self.created.append(run)
        return run

    def get(self, run_id: str) -> RunManifest | None:
        return next((r for r in self.created if r.run_id == run_id), None)

    def list(self, *, limit: int, offset: int) -> Page[RunManifest]:
        return Page(items=self.created, total=len(self.created), limit=limit, offset=offset)

    def transition_status(self, run_id: str, **kwargs: Any) -> RunManifest:
        raise NotImplementedError


class FakeStrategyRepository:
    def __init__(self, spec: StrategySpecV1 | None) -> None:
        self._spec = spec

    def create(self, spec: StrategySpecV1) -> StrategySpecV1:
        return spec

    def get(self, strategy_id: str, version: int) -> StrategySpecV1 | None:
        return self._spec

    def list(self, *, limit: int, offset: int) -> Page[StrategySpecV1]:
        return Page(items=[], total=0, limit=limit, offset=offset)


class FakeDatasetRepository:
    def __init__(self, dataset: DatasetManifest | None) -> None:
        self._dataset = dataset

    def create(self, dataset: DatasetManifest) -> DatasetManifest:
        return dataset

    def get(self, dataset_id: str) -> DatasetManifest | None:
        return self._dataset

    def list(self, *, limit: int, offset: int) -> Page[DatasetManifest]:
        return Page(items=[], total=0, limit=limit, offset=offset)


class FakeInstrumentRepository:
    def __init__(self, instrument: Instrument | None) -> None:
        self._instrument = instrument

    def create(self, instrument: Instrument) -> Instrument:
        return instrument

    def get(self, instrument_id: str) -> Instrument | None:
        return self._instrument

    def list(self, *, limit: int, offset: int) -> Page[Instrument]:
        return Page(items=[], total=0, limit=limit, offset=offset)


def _strategy() -> StrategySpecV1:
    return StrategySpecV1(
        strategy_id="strat-1",
        version=1,
        schema_version=1,
        name="SMA crossover 10/30",
        kind="sma_crossover",
        parameters=SmaCrossoverParameters(fast_window=10, slow_window=30, price_field="close"),
        signal_policy=SignalPolicy(signal_time="bar_close", eligible_after_bars=30, long_only=True),
        created_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        checksum="sha256:aaa",
        canonical_json="{}",
    )


def _dataset(**overrides: Any) -> DatasetManifest:
    defaults: dict[str, Any] = {
        "dataset_id": "ds-1",
        "version": 1,
        "name": "Sample",
        "source_name": "manual",
        "bar_interval": "1d",
        "timezone": "UTC",
        "adjustment_policy": "raw",
        "validation_status": DatasetValidationStatus.VALID,
        "created_at_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "content_checksum": "sha256:bbb",
        "coverage_start_date": date(2020, 1, 1),
        "coverage_end_date": date(2020, 12, 31),
        "instrument_mapping_policy": InstrumentMappingPolicy.TICKER_AS_OF_IMPORT,
    }
    defaults.update(overrides)
    return DatasetManifest(**defaults)


def _instrument() -> Instrument:
    return Instrument(
        instrument_id="ins-1",
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        status=InstrumentStatus.ACTIVE,
        source_name="manual",
        created_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _request(**overrides: Any) -> CreateRunManifestRequest:
    defaults: dict[str, Any] = {
        "strategy_id": "strat-1",
        "strategy_version": 1,
        "dataset_id": "ds-1",
        "instrument_ids": ("ins-1",),
        "start_date": date(2020, 1, 1),
        "end_date": date(2020, 12, 31),
        "capital_amount": "100000000.00",
        "capital_currency": "IDR",
        "position_sizing_fraction": "1.00",
        "quantity_increment": "1",
        "money_scale": 2,
        "annualization_basis": 252,
        "risk_free_rate": "0.00",
    }
    defaults.update(overrides)
    return CreateRunManifestRequest(**defaults)


def test_create_run_manifest_raises_when_strategy_missing() -> None:
    with pytest.raises(StrategySpecNotFoundError):
        create_run_manifest(
            FakeRunRepository(),
            FakeStrategyRepository(None),
            FakeDatasetRepository(_dataset()),
            FakeInstrumentRepository(_instrument()),
            _request(),
        )


def test_create_run_manifest_raises_when_dataset_missing() -> None:
    with pytest.raises(DatasetNotFoundError):
        create_run_manifest(
            FakeRunRepository(),
            FakeStrategyRepository(_strategy()),
            FakeDatasetRepository(None),
            FakeInstrumentRepository(_instrument()),
            _request(),
        )


def test_create_run_manifest_raises_when_instrument_missing() -> None:
    with pytest.raises(InstrumentNotFoundError):
        create_run_manifest(
            FakeRunRepository(),
            FakeStrategyRepository(_strategy()),
            FakeDatasetRepository(_dataset()),
            FakeInstrumentRepository(None),
            _request(),
        )


def test_create_run_manifest_raises_when_period_outside_coverage() -> None:
    with pytest.raises(RunManifestValidationError):
        create_run_manifest(
            FakeRunRepository(),
            FakeStrategyRepository(_strategy()),
            FakeDatasetRepository(_dataset()),
            FakeInstrumentRepository(_instrument()),
            _request(end_date=date(2021, 6, 1)),
        )


def test_create_run_manifest_raises_when_dataset_has_no_coverage() -> None:
    with pytest.raises(RunManifestValidationError):
        create_run_manifest(
            FakeRunRepository(),
            FakeStrategyRepository(_strategy()),
            FakeDatasetRepository(_dataset(coverage_start_date=None, coverage_end_date=None)),
            FakeInstrumentRepository(_instrument()),
            _request(),
        )


def test_create_run_manifest_raises_on_invalid_decimal() -> None:
    with pytest.raises(DecimalFieldError):
        create_run_manifest(
            FakeRunRepository(),
            FakeStrategyRepository(_strategy()),
            FakeDatasetRepository(_dataset()),
            FakeInstrumentRepository(_instrument()),
            _request(capital_amount="not-a-number"),
        )


def test_create_run_manifest_succeeds_and_persists() -> None:
    run_repository = FakeRunRepository()
    run = create_run_manifest(
        run_repository,
        FakeStrategyRepository(_strategy()),
        FakeDatasetRepository(_dataset()),
        FakeInstrumentRepository(_instrument()),
        _request(),
    )

    assert run.status == BacktestRunStatus.CREATED
    assert run.dataset_id == "ds-1"
    assert run.strategy_id == "strat-1"
    assert run.strategy_version == 1
    assert run.schema_version == 1
    assert run.manifest_checksum is not None
    assert run_repository.created == [run]


def test_create_run_manifest_derives_bar_interval_from_dataset() -> None:
    import json

    run = create_run_manifest(
        FakeRunRepository(),
        FakeStrategyRepository(_strategy()),
        FakeDatasetRepository(_dataset(bar_interval="1d")),
        FakeInstrumentRepository(_instrument()),
        _request(),
    )

    manifest = json.loads(run.configuration_json)
    assert manifest["period"]["bar_interval"] == "1d"
