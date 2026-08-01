import hashlib
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.application.errors import CsvContractViolation, DatasetReimportConflictError
from app.application.ports.csv_parser import CsvParser, ParsedRow
from app.application.ports.dataset_import_repository import DatasetImportRepository
from app.application.ports.dataset_import_writer import DatasetImportWriter
from app.domain.dataset import DatasetManifest, DatasetValidationStatus, InstrumentMappingPolicy
from app.domain.market_data import (
    DatasetImport,
    DatasetValidationEvent,
    NormalizedBar,
    ValidationSeverity,
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_ADJUSTMENT_POLICIES = frozenset(
    {"raw", "split_adjusted", "total_return_adjusted", "unknown"}
)


@dataclass(frozen=True, slots=True)
class ImportDatasetRequest:
    raw_bytes: bytes
    filename: str
    name: str
    source_name: str
    license_reference: str
    bar_interval: str
    timezone: str
    adjustment_policy: str
    instrument_mapping_policy: InstrumentMappingPolicy
    source_reference: str | None = None
    allow_reimport: bool = False


def _sanitize_filename(filename: str) -> str:
    return PurePosixPath(filename.replace("\\", "/")).name or "upload.csv"


def _validate_metadata(request: ImportDatasetRequest) -> None:
    for field, value in (
        ("name", request.name),
        ("source_name", request.source_name),
        ("license_reference", request.license_reference),
        ("bar_interval", request.bar_interval),
        ("timezone", request.timezone),
    ):
        if not value.strip():
            raise CsvContractViolation("invalid_metadata", f"{field} must not be empty.")
    if request.adjustment_policy not in ALLOWED_ADJUSTMENT_POLICIES:
        raise CsvContractViolation(
            "invalid_metadata",
            f"adjustment_policy must be one of {sorted(ALLOWED_ADJUSTMENT_POLICIES)}.",
        )
    if request.timezone != "UTC":
        try:
            ZoneInfo(request.timezone)
        except ZoneInfoNotFoundError as exc:
            raise CsvContractViolation(
                "invalid_metadata", f"Unknown timezone: {request.timezone}."
            ) from exc


def _requested_metadata(request: ImportDatasetRequest) -> dict[str, str]:
    return {
        "name": request.name,
        "source_name": request.source_name,
        "source_reference": request.source_reference or "",
        "license_reference": request.license_reference,
        "bar_interval": request.bar_interval,
        "timezone": request.timezone,
        "adjustment_policy": request.adjustment_policy,
        "instrument_mapping_policy": request.instrument_mapping_policy.value,
    }


class ImportDatasetUseCase:
    def __init__(
        self,
        import_repository: DatasetImportRepository,
        import_writer: DatasetImportWriter,
        csv_parser: CsvParser,
        *,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._import_repository = import_repository
        self._import_writer = import_writer
        self._csv_parser = csv_parser
        self._id_factory = id_factory
        self._clock = clock

    def execute(self, request: ImportDatasetRequest) -> DatasetImport:
        started_at = self._clock()
        import_id = self._id_factory()
        content_checksum = hashlib.sha256(request.raw_bytes).hexdigest()
        raw_filename = _sanitize_filename(request.filename)
        requested_metadata_json = json.dumps(_requested_metadata(request), sort_keys=True)
        byte_size = len(request.raw_bytes)

        try:
            _validate_metadata(request)
        except CsvContractViolation as exc:
            return self._reject(
                import_id=import_id,
                raw_filename=raw_filename,
                content_checksum=content_checksum,
                byte_size=byte_size,
                requested_metadata_json=requested_metadata_json,
                started_at=started_at,
                code=exc.code,
                message=exc.message,
                row_number=exc.row_number,
            )

        if byte_size > MAX_UPLOAD_BYTES:
            return self._reject(
                import_id=import_id,
                raw_filename=raw_filename,
                content_checksum=content_checksum,
                byte_size=byte_size,
                requested_metadata_json=requested_metadata_json,
                started_at=started_at,
                code="upload_too_large",
                message=f"File exceeds the maximum upload size of {MAX_UPLOAD_BYTES} bytes.",
                row_number=None,
            )

        if not request.allow_reimport:
            existing = self._import_repository.find_by_content_checksum(content_checksum)
            if existing is not None and existing.dataset_id is not None:
                raise DatasetReimportConflictError(existing.dataset_id)

        try:
            parsed = self._csv_parser.parse(
                request.raw_bytes,
                bar_interval=request.bar_interval,
                timezone_name=request.timezone,
            )
        except CsvContractViolation as exc:
            return self._reject(
                import_id=import_id,
                raw_filename=raw_filename,
                content_checksum=content_checksum,
                byte_size=byte_size,
                requested_metadata_json=requested_metadata_json,
                started_at=started_at,
                code=exc.code,
                message=exc.message,
                row_number=exc.row_number,
            )

        dataset_id = self._id_factory()
        finished_at = self._clock()
        warning_events = self._build_warning_events(
            request,
            parsed_rows=parsed.rows,
            import_id=import_id,
            dataset_id=dataset_id,
            created_at=finished_at,
        )
        status = (
            DatasetValidationStatus.WARNING if warning_events else DatasetValidationStatus.VALID
        )

        dataset = DatasetManifest(
            dataset_id=dataset_id,
            version=1,
            name=request.name,
            source_name=request.source_name,
            source_reference=request.source_reference,
            license_reference=request.license_reference,
            content_checksum=content_checksum,
            bar_interval=request.bar_interval,
            timezone=request.timezone,
            adjustment_policy=request.adjustment_policy,
            coverage_start_date=min(row.timestamp_utc for row in parsed.rows).date(),
            coverage_end_date=max(row.timestamp_utc for row in parsed.rows).date(),
            created_at_utc=finished_at,
            validation_status=status,
            validation_summary=(
                f"{len(warning_events)} warning(s) recorded." if warning_events else None
            ),
            instrument_mapping_policy=request.instrument_mapping_policy,
        )

        bars = [
            NormalizedBar(
                bar_id=self._id_factory(),
                dataset_id=dataset_id,
                source_instrument_identifier=row.instrument_identifier,
                timestamp_utc=row.timestamp_utc,
                bar_interval=request.bar_interval,
                open=row.open,
                high=row.high,
                low=row.low,
                close=row.close,
                volume=row.volume,
                currency=row.currency,
                source_row_id=row.source_row_id,
            )
            for row in parsed.rows
        ]

        import_record = DatasetImport(
            import_id=import_id,
            dataset_id=dataset_id,
            raw_filename=raw_filename,
            content_checksum=content_checksum,
            byte_size=byte_size,
            requested_metadata_json=requested_metadata_json,
            status=status,
            row_count=len(parsed.rows),
            accepted_row_count=len(parsed.rows),
            warning_count=len(warning_events),
            error_count=0,
            started_at_utc=started_at,
            finished_at_utc=finished_at,
        )

        self._import_writer.persist_accepted_import(
            dataset=dataset,
            bars=bars,
            import_record=import_record,
            warning_events=warning_events,
        )
        return import_record

    def _build_warning_events(
        self,
        request: ImportDatasetRequest,
        *,
        parsed_rows: list[ParsedRow],
        import_id: str,
        dataset_id: str,
        created_at: datetime,
    ) -> list[DatasetValidationEvent]:
        events: list[DatasetValidationEvent] = []
        if request.adjustment_policy == "unknown":
            events.append(
                DatasetValidationEvent(
                    event_id=self._id_factory(),
                    import_id=import_id,
                    dataset_id=dataset_id,
                    severity=ValidationSeverity.WARNING,
                    code="unknown_adjustment_policy",
                    message="Dataset was imported with adjustment_policy=unknown.",
                    created_at_utc=created_at,
                )
            )
        zero_volume_count = sum(1 for row in parsed_rows if row.zero_volume)
        if zero_volume_count:
            events.append(
                DatasetValidationEvent(
                    event_id=self._id_factory(),
                    import_id=import_id,
                    dataset_id=dataset_id,
                    severity=ValidationSeverity.WARNING,
                    code="zero_volume_bars",
                    message=f"{zero_volume_count} row(s) have zero volume.",
                    created_at_utc=created_at,
                )
            )
        return events

    def _reject(
        self,
        *,
        import_id: str,
        raw_filename: str,
        content_checksum: str,
        byte_size: int,
        requested_metadata_json: str,
        started_at: datetime,
        code: str,
        message: str,
        row_number: int | None,
    ) -> DatasetImport:
        finished_at = self._clock()
        error_event = DatasetValidationEvent(
            event_id=self._id_factory(),
            import_id=import_id,
            dataset_id=None,
            severity=ValidationSeverity.ERROR,
            code=code,
            message=message,
            source_row_number=row_number,
            created_at_utc=finished_at,
        )
        import_record = DatasetImport(
            import_id=import_id,
            dataset_id=None,
            raw_filename=raw_filename,
            content_checksum=content_checksum,
            byte_size=byte_size,
            requested_metadata_json=requested_metadata_json,
            status=DatasetValidationStatus.REJECTED,
            row_count=0,
            accepted_row_count=0,
            warning_count=0,
            error_count=1,
            started_at_utc=started_at,
            finished_at_utc=finished_at,
            failure_code=code,
            failure_row_number=row_number,
        )
        self._import_writer.persist_rejected_import(
            import_record=import_record, error_event=error_event
        )
        return import_record
