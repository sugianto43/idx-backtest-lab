from app.application.dataset_import_service import ImportDatasetRequest, ImportDatasetUseCase
from app.domain.dataset import InstrumentMappingPolicy
from app.infrastructure.db.dataset_import_repository import DuckDBDatasetImportRepository
from app.infrastructure.db.dataset_import_writer import DuckDBDatasetImportWriter
from app.infrastructure.ingestion.csv_parser import DelimitedCsvParser
from app.infrastructure.settings import Settings

DEFAULT_DATASET_CSV = (
    b"timestamp,instrument_identifier,open,high,low,close,volume\n"
    b"2020-01-01,BBCA,100,105,99,104,1000\n"
    b"2020-01-02,BBCA,104,110,103,109,1500\n"
)


def seed_dataset(
    settings: Settings,
    *,
    name: str = "Sample dataset",
    raw_bytes: bytes = DEFAULT_DATASET_CSV,
    instrument_mapping_policy: (
        InstrumentMappingPolicy
    ) = InstrumentMappingPolicy.TICKER_AS_OF_IMPORT,
) -> str:
    """Seeds a dataset directly through the import use case.

    The manual CSV-upload HTTP endpoint was removed (TASK-018); tests still need a
    deterministic, network-free way to get a valid dataset on disk, so they call the
    same use case the Yahoo Finance import route calls instead of going over HTTP.
    """
    use_case = ImportDatasetUseCase(
        import_repository=DuckDBDatasetImportRepository(settings),
        import_writer=DuckDBDatasetImportWriter(settings),
        csv_parser=DelimitedCsvParser(),
    )
    result = use_case.execute(
        ImportDatasetRequest(
            raw_bytes=raw_bytes,
            filename="prices.csv",
            name=name,
            source_name="Manual export",
            license_reference="user_supplied_unknown",
            bar_interval="1d",
            timezone="UTC",
            adjustment_policy="raw",
            instrument_mapping_policy=instrument_mapping_policy,
        )
    )
    assert result.dataset_id is not None
    return result.dataset_id
