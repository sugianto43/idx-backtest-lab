from fastapi import APIRouter, Depends, Query, status

from app.api.errors import AppError, NotFoundError
from app.api.schemas.datasets import (
    DatasetDetailResponse,
    DatasetImportResponse,
    DatasetListResponse,
    DatasetSummary,
    DatasetWarning,
    ImportFromYahooFinanceRequest,
)
from app.application.dataset_import_service import ImportDatasetRequest, ImportDatasetUseCase
from app.application.errors import DatasetReimportConflictError
from app.domain.dataset import DatasetValidationStatus
from app.domain.market_data import DatasetImport
from app.infrastructure.db.dataset_import_repository import DuckDBDatasetImportRepository
from app.infrastructure.db.dataset_import_writer import DuckDBDatasetImportWriter
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.dataset_validation_event_repository import (
    DuckDBDatasetValidationEventRepository,
)
from app.infrastructure.ingestion.csv_parser import DelimitedCsvParser
from app.infrastructure.market_data.yahoo_finance_provider import (
    YAHOO_FINANCE_ADJUSTMENT_POLICY,
    YAHOO_FINANCE_LICENSE_REFERENCE,
    YAHOO_FINANCE_SOURCE_NAME,
    YahooFinanceFetchError,
    fetch_daily_ohlcv_csv,
)
from app.infrastructure.settings import Settings, get_settings

v1_datasets_router = APIRouter(prefix="/api/v1")


class DatasetImportRejectedError(AppError):
    code = "validation_error"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "The dataset import was rejected."


class DatasetConflictError(AppError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "An identical dataset has already been imported."


class YahooFinanceFetchHttpError(AppError):
    code = "upstream_fetch_failed"
    status_code = status.HTTP_502_BAD_GATEWAY
    message = "Could not fetch data from Yahoo Finance."


def _build_use_case(settings: Settings) -> ImportDatasetUseCase:
    return ImportDatasetUseCase(
        import_repository=DuckDBDatasetImportRepository(settings),
        import_writer=DuckDBDatasetImportWriter(settings),
        csv_parser=DelimitedCsvParser(),
    )


def _get_use_case(settings: Settings = Depends(get_settings)) -> ImportDatasetUseCase:
    return _build_use_case(settings)


def _import_response_or_raise(result: DatasetImport) -> DatasetImportResponse:
    if result.status == DatasetValidationStatus.REJECTED:
        raise DatasetImportRejectedError(
            details=[
                {
                    "code": result.failure_code,
                    "row_number": result.failure_row_number,
                }
            ]
        )

    return DatasetImportResponse(
        import_id=result.import_id,
        dataset_id=result.dataset_id,
        status=result.status.value,  # type: ignore[arg-type]
        row_count=result.row_count,
        accepted_row_count=result.accepted_row_count,
        warning_count=result.warning_count,
        started_at_utc=result.started_at_utc,
        finished_at_utc=result.finished_at_utc,
    )


@v1_datasets_router.post(
    "/datasets:import-from-yahoo-finance",
    response_model=DatasetImportResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_dataset_from_yahoo_finance(
    payload: ImportFromYahooFinanceRequest,
    use_case: ImportDatasetUseCase = Depends(_get_use_case),
) -> DatasetImportResponse:
    try:
        csv_bytes = fetch_daily_ohlcv_csv(
            payload.ticker,
            payload.instrument_identifier or payload.ticker,
            payload.start_date,
            payload.end_date,
        )
    except YahooFinanceFetchError as exc:
        raise YahooFinanceFetchHttpError(
            details=[{"code": exc.code, "message": exc.message}]
        ) from exc

    try:
        result = use_case.execute(
            ImportDatasetRequest(
                raw_bytes=csv_bytes,
                filename=f"{payload.ticker}.csv",
                name=payload.name,
                source_name=YAHOO_FINANCE_SOURCE_NAME,
                license_reference=YAHOO_FINANCE_LICENSE_REFERENCE,
                bar_interval="1d",
                timezone="UTC",
                adjustment_policy=YAHOO_FINANCE_ADJUSTMENT_POLICY,
                instrument_mapping_policy=payload.instrument_mapping_policy,
                source_reference=f"ticker={payload.ticker}",
                allow_reimport=payload.allow_reimport,
            )
        )
    except DatasetReimportConflictError as exc:
        raise DatasetConflictError(
            details=[{"existing_dataset_id": exc.existing_dataset_id}]
        ) from exc

    return _import_response_or_raise(result)


@v1_datasets_router.get("/datasets/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: str, settings: Settings = Depends(get_settings)
) -> DatasetDetailResponse:
    dataset_repository = DuckDBDatasetRepository(settings)
    dataset = dataset_repository.get(dataset_id)
    if dataset is None:
        raise NotFoundError()

    import_repository = DuckDBDatasetImportRepository(settings)
    latest_import = import_repository.get_latest_for_dataset(dataset_id)
    row_count = latest_import.accepted_row_count if latest_import else 0
    warning_count = latest_import.warning_count if latest_import else 0

    event_repository = DuckDBDatasetValidationEventRepository(settings)
    warnings_page = event_repository.list_for_dataset(dataset_id, limit=100, offset=0)

    return DatasetDetailResponse(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        source_name=dataset.source_name,
        source_reference=dataset.source_reference,
        license_reference=dataset.license_reference,
        bar_interval=dataset.bar_interval,
        timezone=dataset.timezone,
        adjustment_policy=dataset.adjustment_policy,
        instrument_mapping_policy=dataset.instrument_mapping_policy,
        coverage_start_date=dataset.coverage_start_date,
        coverage_end_date=dataset.coverage_end_date,
        validation_status=dataset.validation_status.value,
        validation_summary=dataset.validation_summary,
        created_at_utc=dataset.created_at_utc,
        row_count=row_count,
        warning_count=warning_count,
        warnings=[
            DatasetWarning(
                code=event.code,
                message=event.message,
                source_row_number=event.source_row_number,
                created_at_utc=event.created_at_utc,
            )
            for event in warnings_page.items
        ],
    )


@v1_datasets_router.get("/datasets", response_model=DatasetListResponse)
def list_datasets(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> DatasetListResponse:
    page = DuckDBDatasetRepository(settings).list(limit=limit, offset=offset)
    import_repository = DuckDBDatasetImportRepository(settings)

    items = []
    for dataset in page.items:
        latest_import = import_repository.get_latest_for_dataset(dataset.dataset_id)
        items.append(
            DatasetSummary(
                dataset_id=dataset.dataset_id,
                name=dataset.name,
                source_name=dataset.source_name,
                source_reference=dataset.source_reference,
                license_reference=dataset.license_reference,
                bar_interval=dataset.bar_interval,
                timezone=dataset.timezone,
                adjustment_policy=dataset.adjustment_policy,
                instrument_mapping_policy=dataset.instrument_mapping_policy,
                coverage_start_date=dataset.coverage_start_date,
                coverage_end_date=dataset.coverage_end_date,
                validation_status=dataset.validation_status.value,
                validation_summary=dataset.validation_summary,
                created_at_utc=dataset.created_at_utc,
                row_count=latest_import.accepted_row_count if latest_import else 0,
                warning_count=latest_import.warning_count if latest_import else 0,
            )
        )

    return DatasetListResponse(items=items, total=page.total, limit=page.limit, offset=page.offset)
