from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.application.dataset_import_service import ImportDatasetRequest, ImportDatasetUseCase
from app.application.errors import CsvContractViolation, DatasetReimportConflictError
from app.application.ports.csv_parser import ParsedImport, ParsedRow
from app.domain.dataset import DatasetValidationStatus, InstrumentMappingPolicy
from app.domain.market_data import DatasetImport


class FakeCsvParser:
    def __init__(self, result: ParsedImport | None = None, error: Exception | None = None) -> None:
        self._result = result
        self._error = error

    def parse(self, raw_bytes: bytes, *, bar_interval: str, timezone_name: str) -> ParsedImport:
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


class FakeImportRepository:
    def __init__(self) -> None:
        self.by_checksum: dict[str, DatasetImport] = {}

    def get(self, import_id: str) -> DatasetImport | None:
        return None

    def find_by_content_checksum(self, content_checksum: str) -> DatasetImport | None:
        return self.by_checksum.get(content_checksum)

    def get_latest_for_dataset(self, dataset_id: str) -> DatasetImport | None:
        return None


class FakeImportWriter:
    def __init__(self) -> None:
        self.accepted: list[dict[str, Any]] = []
        self.rejected: list[dict[str, Any]] = []

    def persist_accepted_import(self, **kwargs: Any) -> None:
        self.accepted.append(kwargs)

    def persist_rejected_import(self, **kwargs: Any) -> None:
        self.rejected.append(kwargs)


def _row(**overrides: Any) -> ParsedRow:
    defaults: dict[str, Any] = {
        "row_number": 2,
        "instrument_identifier": "BBCA",
        "timestamp_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "open": Decimal("100"),
        "high": Decimal("105"),
        "low": Decimal("99"),
        "close": Decimal("104"),
        "volume": 1000,
        "currency": None,
        "source_row_id": None,
        "zero_volume": False,
    }
    defaults.update(overrides)
    return ParsedRow(**defaults)


def _request(**overrides: Any) -> ImportDatasetRequest:
    defaults: dict[str, Any] = {
        "raw_bytes": b"irrelevant-for-fake-parser",
        "filename": "prices.csv",
        "name": "Sample",
        "source_name": "Manual export",
        "license_reference": "user_supplied_unknown",
        "bar_interval": "1d",
        "timezone": "UTC",
        "adjustment_policy": "raw",
        "instrument_mapping_policy": InstrumentMappingPolicy.TICKER_AS_OF_IMPORT,
    }
    defaults.update(overrides)
    return ImportDatasetRequest(**defaults)


def _use_case(
    parser: FakeCsvParser, repository: FakeImportRepository | None = None
) -> tuple[ImportDatasetUseCase, FakeImportRepository, FakeImportWriter]:
    repo = repository or FakeImportRepository()
    writer = FakeImportWriter()
    use_case = ImportDatasetUseCase(repo, writer, parser, id_factory=_sequential_ids())
    return use_case, repo, writer


def _sequential_ids() -> Any:
    counter = iter(range(1, 1000))

    def factory() -> str:
        return f"id-{next(counter)}"

    return factory


def test_valid_import_persists_accepted_with_no_warnings() -> None:
    parser = FakeCsvParser(result=ParsedImport(rows=[_row()]))
    use_case, _repo, writer = _use_case(parser)

    result = use_case.execute(_request())

    assert result.status == DatasetValidationStatus.VALID
    assert result.warning_count == 0
    assert len(writer.accepted) == 1
    assert writer.accepted[0]["warning_events"] == []
    assert writer.accepted[0]["dataset"].coverage_start_date == datetime(2026, 1, 1).date()


def test_unknown_adjustment_policy_creates_warning() -> None:
    parser = FakeCsvParser(result=ParsedImport(rows=[_row()]))
    use_case, _repo, writer = _use_case(parser)

    result = use_case.execute(_request(adjustment_policy="unknown"))

    assert result.status == DatasetValidationStatus.WARNING
    assert result.warning_count == 1
    codes = [event.code for event in writer.accepted[0]["warning_events"]]
    assert "unknown_adjustment_policy" in codes


def test_zero_volume_rows_create_warning_without_changing_bar_values() -> None:
    parser = FakeCsvParser(result=ParsedImport(rows=[_row(zero_volume=True, volume=0)]))
    use_case, _repo, writer = _use_case(parser)

    result = use_case.execute(_request())

    assert result.status == DatasetValidationStatus.WARNING
    bars = writer.accepted[0]["bars"]
    assert bars[0].volume == 0
    codes = [event.code for event in writer.accepted[0]["warning_events"]]
    assert "zero_volume_bars" in codes


def test_csv_contract_violation_rejects_and_persists_audit_record() -> None:
    parser = FakeCsvParser(error=CsvContractViolation("invalid_header", "bad header", None))
    use_case, _repo, writer = _use_case(parser)

    result = use_case.execute(_request())

    assert result.status == DatasetValidationStatus.REJECTED
    assert result.failure_code == "invalid_header"
    assert result.dataset_id is None
    assert len(writer.rejected) == 1
    assert writer.accepted == []


def test_invalid_metadata_rejects_before_parsing() -> None:
    parser = FakeCsvParser(result=ParsedImport(rows=[_row()]))
    use_case, _repo, writer = _use_case(parser)

    result = use_case.execute(_request(name="   "))

    assert result.status == DatasetValidationStatus.REJECTED
    assert result.failure_code == "invalid_metadata"
    assert writer.accepted == []


def test_upload_too_large_rejects_without_parsing() -> None:
    parser = FakeCsvParser(result=ParsedImport(rows=[_row()]))
    use_case, _repo, writer = _use_case(parser)

    huge_request = _request(raw_bytes=b"x" * (10 * 1024 * 1024 + 1))
    result = use_case.execute(huge_request)

    assert result.status == DatasetValidationStatus.REJECTED
    assert result.failure_code == "upload_too_large"


def test_reimport_conflict_raises_when_not_explicitly_allowed() -> None:
    repository = FakeImportRepository()
    existing = DatasetImport(
        import_id="imp-existing",
        dataset_id="ds-existing",
        raw_filename="prices.csv",
        content_checksum="checksum-1",
        byte_size=10,
        requested_metadata_json="{}",
        status=DatasetValidationStatus.VALID,
        row_count=1,
        accepted_row_count=1,
        warning_count=0,
        error_count=0,
        started_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        finished_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )
    parser = FakeCsvParser(result=ParsedImport(rows=[_row()]))
    use_case, repo, _writer = _use_case(parser, repository)

    import hashlib

    checksum = hashlib.sha256(b"irrelevant-for-fake-parser").hexdigest()
    repo.by_checksum[checksum] = existing

    with pytest.raises(DatasetReimportConflictError) as excinfo:
        use_case.execute(_request())
    assert excinfo.value.existing_dataset_id == "ds-existing"


def test_allow_reimport_bypasses_conflict_check() -> None:
    repository = FakeImportRepository()
    parser = FakeCsvParser(result=ParsedImport(rows=[_row()]))
    use_case, repo, writer = _use_case(parser, repository)

    import hashlib

    checksum = hashlib.sha256(b"irrelevant-for-fake-parser").hexdigest()
    repo.by_checksum[checksum] = DatasetImport(
        import_id="imp-existing",
        dataset_id="ds-existing",
        raw_filename="prices.csv",
        content_checksum=checksum,
        byte_size=10,
        requested_metadata_json="{}",
        status=DatasetValidationStatus.VALID,
        row_count=1,
        accepted_row_count=1,
        warning_count=0,
        error_count=0,
        started_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
        finished_at_utc=datetime(2026, 1, 1, tzinfo=UTC),
    )

    result = use_case.execute(_request(allow_reimport=True))

    assert result.status == DatasetValidationStatus.VALID
    assert len(writer.accepted) == 1
