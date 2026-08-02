from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.application.corporate_action_service import record_corporate_action
from app.application.dataset_instrument_mapping_service import create_dataset_instrument_mapping
from app.application.errors import (
    AliasOverlapError,
    CorporateActionNotFoundError,
    DatasetNotFoundError,
    InstrumentNotFoundError,
    MappingOverlapError,
)
from app.application.instrument_service import add_instrument_alias, create_instrument
from app.domain.corporate_action import CorporateAction, CorporateActionType
from app.domain.dataset import DatasetManifest, DatasetValidationStatus
from app.domain.instrument import AliasConfidence, Instrument, InstrumentAlias, InstrumentType
from app.domain.pagination import Page


class FakeInstrumentRepository:
    def __init__(self) -> None:
        self.items: dict[str, Instrument] = {}

    def create(self, instrument: Instrument) -> Instrument:
        self.items[instrument.instrument_id] = instrument
        return instrument

    def get(self, instrument_id: str) -> Instrument | None:
        return self.items.get(instrument_id)

    def list(self, *, limit: int, offset: int) -> Page[Instrument]:
        values = list(self.items.values())
        return Page(
            items=values[offset : offset + limit], total=len(values), limit=limit, offset=offset
        )


class FakeAliasRepository:
    def __init__(self, overlap: bool = False) -> None:
        self.created: list[InstrumentAlias] = []
        self._overlap = overlap

    def create(self, alias: InstrumentAlias) -> InstrumentAlias:
        self.created.append(alias)
        return alias

    def list_for_instrument(self, instrument_id: str) -> list[InstrumentAlias]:
        return [a for a in self.created if a.instrument_id == instrument_id]

    def find_overlapping(self, **kwargs: Any) -> list[InstrumentAlias]:
        if not self._overlap:
            return []
        return [
            InstrumentAlias(
                alias_id="existing-alias",
                instrument_id="some-other-instrument",
                symbol=kwargs.get("symbol", "BBCA"),
                exchange_code=kwargs.get("exchange_code", "IDX"),
                effective_from=date(2019, 1, 1),
                source_name="manual",
                confidence=AliasConfidence.CONFIRMED,
                created_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
            )
        ]


def _sequential_ids() -> Any:
    counter = iter(range(1, 1000))

    def factory() -> str:
        return f"id-{next(counter)}"

    return factory


def test_create_instrument_persists() -> None:
    repository = FakeInstrumentRepository()
    instrument = create_instrument(
        repository,
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        source_name="manual",
        id_factory=_sequential_ids(),
        clock=lambda: datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert repository.get(instrument.instrument_id) == instrument


def test_add_alias_raises_when_instrument_missing() -> None:
    with pytest.raises(InstrumentNotFoundError):
        add_instrument_alias(
            FakeAliasRepository(),
            FakeInstrumentRepository(),
            instrument_id="missing",
            symbol="BBCA",
            exchange_code="IDX",
            effective_from=date(2020, 1, 1),
            source_name="manual",
            confidence=AliasConfidence.CONFIRMED,
        )


def test_add_alias_raises_on_overlap() -> None:
    instrument_repository = FakeInstrumentRepository()
    instrument = create_instrument(
        instrument_repository,
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        source_name="manual",
        id_factory=_sequential_ids(),
    )
    with pytest.raises(AliasOverlapError):
        add_instrument_alias(
            FakeAliasRepository(overlap=True),
            instrument_repository,
            instrument_id=instrument.instrument_id,
            symbol="BBCA",
            exchange_code="IDX",
            effective_from=date(2020, 1, 1),
            source_name="manual",
            confidence=AliasConfidence.CONFIRMED,
        )


def test_add_alias_succeeds_when_no_overlap() -> None:
    instrument_repository = FakeInstrumentRepository()
    instrument = create_instrument(
        instrument_repository,
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        source_name="manual",
        id_factory=_sequential_ids(),
    )
    alias = add_instrument_alias(
        FakeAliasRepository(overlap=False),
        instrument_repository,
        instrument_id=instrument.instrument_id,
        symbol="BBCA",
        exchange_code="IDX",
        effective_from=date(2020, 1, 1),
        source_name="manual",
        confidence=AliasConfidence.CONFIRMED,
    )
    assert alias.symbol == "BBCA"


class FakeDatasetRepository:
    def __init__(self, dataset: DatasetManifest | None) -> None:
        self._dataset = dataset

    def create(self, dataset: DatasetManifest) -> DatasetManifest:
        return dataset

    def get(self, dataset_id: str) -> DatasetManifest | None:
        return self._dataset

    def list(self, *, limit: int, offset: int) -> Page[DatasetManifest]:
        return Page(items=[], total=0, limit=limit, offset=offset)


class FakeMappingRepository:
    def __init__(self, overlap: bool = False) -> None:
        self.created: list[Any] = []
        self._overlap = overlap

    def create(self, mapping: Any) -> Any:
        self.created.append(mapping)
        return mapping

    def list_for_dataset(self, dataset_id: str) -> list[Any]:
        return self.created

    def list_for_instrument(self, instrument_id: str) -> list[Any]:
        return self.created

    def find_overlapping(self, **kwargs: Any) -> list[Any]:
        return ["existing-mapping"] if self._overlap else []


def _dataset() -> DatasetManifest:
    return DatasetManifest(
        dataset_id="ds-1",
        version=1,
        name="Sample",
        source_name="Manual export",
        bar_interval="1d",
        timezone="UTC",
        adjustment_policy="raw",
        validation_status=DatasetValidationStatus.VALID,
        created_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_create_mapping_raises_when_dataset_missing() -> None:
    with pytest.raises(DatasetNotFoundError):
        create_dataset_instrument_mapping(
            FakeMappingRepository(),
            FakeDatasetRepository(None),
            FakeInstrumentRepository(),
            dataset_id="ds-1",
            source_instrument_identifier="BBCA",
            instrument_id="ins-1",
            effective_from=date(2020, 1, 1),
            decision_source="manual_review",
        )


def test_create_mapping_raises_when_instrument_missing() -> None:
    with pytest.raises(InstrumentNotFoundError):
        create_dataset_instrument_mapping(
            FakeMappingRepository(),
            FakeDatasetRepository(_dataset()),
            FakeInstrumentRepository(),
            dataset_id="ds-1",
            source_instrument_identifier="BBCA",
            instrument_id="ins-1",
            effective_from=date(2020, 1, 1),
            decision_source="manual_review",
        )


def test_create_mapping_raises_on_overlap() -> None:
    instrument_repository = FakeInstrumentRepository()
    instrument = create_instrument(
        instrument_repository,
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        source_name="manual",
        id_factory=_sequential_ids(),
    )
    with pytest.raises(MappingOverlapError):
        create_dataset_instrument_mapping(
            FakeMappingRepository(overlap=True),
            FakeDatasetRepository(_dataset()),
            instrument_repository,
            dataset_id="ds-1",
            source_instrument_identifier="BBCA",
            instrument_id=instrument.instrument_id,
            effective_from=date(2020, 1, 1),
            decision_source="manual_review",
        )


def test_create_mapping_succeeds() -> None:
    instrument_repository = FakeInstrumentRepository()
    instrument = create_instrument(
        instrument_repository,
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        source_name="manual",
        id_factory=_sequential_ids(),
    )
    mapping = create_dataset_instrument_mapping(
        FakeMappingRepository(overlap=False),
        FakeDatasetRepository(_dataset()),
        instrument_repository,
        dataset_id="ds-1",
        source_instrument_identifier="BBCA",
        instrument_id=instrument.instrument_id,
        effective_from=date(2020, 1, 1),
        decision_source="manual_review",
        id_factory=_sequential_ids(),
    )
    assert mapping.source_instrument_identifier == "BBCA"


class FakeCorporateActionRepository:
    def __init__(self, existing: CorporateAction | None = None) -> None:
        self.created: list[CorporateAction] = []
        self._existing = existing

    def create(self, action: CorporateAction) -> CorporateAction:
        self.created.append(action)
        return action

    def get(self, event_id: str) -> CorporateAction | None:
        return self._existing

    def list_for_instrument(
        self, instrument_id: str, *, limit: int, offset: int
    ) -> Page[CorporateAction]:
        return Page(items=self.created, total=len(self.created), limit=limit, offset=offset)


def test_record_corporate_action_raises_when_instrument_missing() -> None:
    with pytest.raises(InstrumentNotFoundError):
        record_corporate_action(
            FakeCorporateActionRepository(),
            FakeInstrumentRepository(),
            instrument_id="missing",
            event_type=CorporateActionType.CASH_DIVIDEND,
            effective_date=date(2026, 1, 1),
            source_name="manual",
            payload_json="{}",
        )


def test_record_corporate_action_raises_when_superseded_missing() -> None:
    instrument_repository = FakeInstrumentRepository()
    instrument = create_instrument(
        instrument_repository,
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        source_name="manual",
        id_factory=_sequential_ids(),
    )
    with pytest.raises(CorporateActionNotFoundError):
        record_corporate_action(
            FakeCorporateActionRepository(existing=None),
            instrument_repository,
            instrument_id=instrument.instrument_id,
            event_type=CorporateActionType.CASH_DIVIDEND,
            effective_date=date(2026, 1, 1),
            source_name="manual",
            payload_json="{}",
            supersedes_event_id="does-not-exist",
        )


def test_record_corporate_action_succeeds() -> None:
    instrument_repository = FakeInstrumentRepository()
    instrument = create_instrument(
        instrument_repository,
        instrument_type=InstrumentType.EQUITY,
        display_name="Bank Central Asia",
        source_name="manual",
        id_factory=_sequential_ids(),
    )
    action = record_corporate_action(
        FakeCorporateActionRepository(),
        instrument_repository,
        instrument_id=instrument.instrument_id,
        event_type=CorporateActionType.CASH_DIVIDEND,
        effective_date=date(2026, 1, 1),
        source_name="manual",
        payload_json='{"amount_per_share": "150"}',
        id_factory=_sequential_ids(),
    )
    assert action.instrument_id == instrument.instrument_id
