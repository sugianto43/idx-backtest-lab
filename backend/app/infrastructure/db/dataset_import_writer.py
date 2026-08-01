from typing import Any

from app.domain.dataset import DatasetManifest
from app.domain.market_data import DatasetImport, DatasetValidationEvent, NormalizedBar
from app.infrastructure.db.connection import connect
from app.infrastructure.db.serialization import to_naive_utc
from app.infrastructure.settings import Settings

_DATASET_COLUMNS = (
    "dataset_id",
    "version",
    "name",
    "source_name",
    "source_reference",
    "license_reference",
    "content_checksum",
    "bar_interval",
    "timezone",
    "adjustment_policy",
    "coverage_start_date",
    "coverage_end_date",
    "created_at_utc",
    "validation_status",
    "validation_summary",
    "instrument_mapping_policy",
)

_BAR_COLUMNS = (
    "bar_id",
    "dataset_id",
    "source_instrument_identifier",
    "timestamp_utc",
    "bar_interval",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "currency",
    "source_row_id",
)

_IMPORT_COLUMNS = (
    "import_id",
    "dataset_id",
    "raw_filename",
    "content_checksum",
    "byte_size",
    "requested_metadata",
    "status",
    "row_count",
    "accepted_row_count",
    "warning_count",
    "error_count",
    "started_at_utc",
    "finished_at_utc",
    "failure_code",
    "failure_row_number",
)

_EVENT_COLUMNS = (
    "event_id",
    "import_id",
    "dataset_id",
    "severity",
    "code",
    "message",
    "source_row_number",
    "created_at_utc",
)


def _dataset_values(dataset: DatasetManifest) -> list[Any]:
    return [
        dataset.dataset_id,
        dataset.version,
        dataset.name,
        dataset.source_name,
        dataset.source_reference,
        dataset.license_reference,
        dataset.content_checksum,
        dataset.bar_interval,
        dataset.timezone,
        dataset.adjustment_policy,
        dataset.coverage_start_date,
        dataset.coverage_end_date,
        to_naive_utc(dataset.created_at_utc),
        dataset.validation_status.value,
        dataset.validation_summary,
        dataset.instrument_mapping_policy.value,
    ]


def _bar_values(bar: NormalizedBar) -> list[Any]:
    return [
        bar.bar_id,
        bar.dataset_id,
        bar.source_instrument_identifier,
        to_naive_utc(bar.timestamp_utc),
        bar.bar_interval,
        bar.open,
        bar.high,
        bar.low,
        bar.close,
        bar.volume,
        bar.currency,
        bar.source_row_id,
    ]


def _import_values(import_record: DatasetImport) -> list[Any]:
    return [
        import_record.import_id,
        import_record.dataset_id,
        import_record.raw_filename,
        import_record.content_checksum,
        import_record.byte_size,
        import_record.requested_metadata_json,
        import_record.status.value,
        import_record.row_count,
        import_record.accepted_row_count,
        import_record.warning_count,
        import_record.error_count,
        to_naive_utc(import_record.started_at_utc),
        to_naive_utc(import_record.finished_at_utc),
        import_record.failure_code,
        import_record.failure_row_number,
    ]


def _event_values(event: DatasetValidationEvent) -> list[Any]:
    return [
        event.event_id,
        event.import_id,
        event.dataset_id,
        event.severity.value,
        event.code,
        event.message,
        event.source_row_number,
        to_naive_utc(event.created_at_utc),
    ]


class DuckDBDatasetImportWriter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def persist_accepted_import(
        self,
        *,
        dataset: DatasetManifest,
        bars: list[NormalizedBar],
        import_record: DatasetImport,
        warning_events: list[DatasetValidationEvent],
    ) -> None:
        with connect(self._settings) as connection:
            try:
                connection.execute("BEGIN TRANSACTION")
                connection.execute(
                    f"""
                    INSERT INTO datasets ({", ".join(_DATASET_COLUMNS)})
                    VALUES ({", ".join("?" for _ in _DATASET_COLUMNS)})
                    """,
                    _dataset_values(dataset),
                )
                if bars:
                    connection.executemany(
                        f"""
                        INSERT INTO normalized_bars ({", ".join(_BAR_COLUMNS)})
                        VALUES ({", ".join("?" for _ in _BAR_COLUMNS)})
                        """,
                        [_bar_values(bar) for bar in bars],
                    )
                connection.execute(
                    f"""
                    INSERT INTO dataset_imports ({", ".join(_IMPORT_COLUMNS)})
                    VALUES ({", ".join("?" for _ in _IMPORT_COLUMNS)})
                    """,
                    _import_values(import_record),
                )
                if warning_events:
                    connection.executemany(
                        f"""
                        INSERT INTO dataset_validation_events ({", ".join(_EVENT_COLUMNS)})
                        VALUES ({", ".join("?" for _ in _EVENT_COLUMNS)})
                        """,
                        [_event_values(event) for event in warning_events],
                    )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def persist_rejected_import(
        self,
        *,
        import_record: DatasetImport,
        error_event: DatasetValidationEvent,
    ) -> None:
        with connect(self._settings) as connection:
            try:
                connection.execute("BEGIN TRANSACTION")
                connection.execute(
                    f"""
                    INSERT INTO dataset_imports ({", ".join(_IMPORT_COLUMNS)})
                    VALUES ({", ".join("?" for _ in _IMPORT_COLUMNS)})
                    """,
                    _import_values(import_record),
                )
                connection.execute(
                    f"""
                    INSERT INTO dataset_validation_events ({", ".join(_EVENT_COLUMNS)})
                    VALUES ({", ".join("?" for _ in _EVENT_COLUMNS)})
                    """,
                    _event_values(error_event),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
