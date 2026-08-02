import json

from fastapi import APIRouter, Depends, Query, status

from app.api.errors import AppError, NotFoundError
from app.api.schemas.instruments import (
    AddAliasRequest,
    AliasResponse,
    CorporateActionListResponse,
    CorporateActionResponse,
    CreateInstrumentRequest,
    CreateMappingRequest,
    DatasetMappingListResponse,
    InstrumentDetailResponse,
    InstrumentListResponse,
    InstrumentResponse,
    MappingResponse,
    MappingSummary,
    RecordCorporateActionRequest,
)
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
from app.domain.corporate_action import CorporateAction
from app.domain.instrument import DatasetInstrumentMapping, Instrument, InstrumentAlias
from app.infrastructure.db.corporate_action_repository import DuckDBCorporateActionRepository
from app.infrastructure.db.dataset_instrument_mapping_repository import (
    DuckDBDatasetInstrumentMappingRepository,
)
from app.infrastructure.db.dataset_repository import DuckDBDatasetRepository
from app.infrastructure.db.instrument_alias_repository import DuckDBInstrumentAliasRepository
from app.infrastructure.db.instrument_repository import DuckDBInstrumentRepository
from app.infrastructure.settings import Settings, get_settings

v1_instruments_router = APIRouter(prefix="/api/v1")


class ConflictError(AppError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "The request conflicts with existing data."


def _instrument_response(instrument: Instrument) -> InstrumentResponse:
    return InstrumentResponse(
        instrument_id=instrument.instrument_id,
        instrument_type=instrument.instrument_type,
        display_name=instrument.display_name,
        currency=instrument.currency,
        status=instrument.status,
        source_name=instrument.source_name,
        source_reference=instrument.source_reference,
        created_at_utc=instrument.created_at_utc,
    )


def _alias_response(alias: InstrumentAlias) -> AliasResponse:
    return AliasResponse(
        alias_id=alias.alias_id,
        instrument_id=alias.instrument_id,
        symbol=alias.symbol,
        exchange_code=alias.exchange_code,
        effective_from=alias.effective_from,
        effective_to=alias.effective_to,
        source_name=alias.source_name,
        source_reference=alias.source_reference,
        confidence=alias.confidence,
        created_at_utc=alias.created_at_utc,
    )


def _mapping_response(mapping: DatasetInstrumentMapping) -> MappingResponse:
    return MappingResponse(
        mapping_id=mapping.mapping_id,
        dataset_id=mapping.dataset_id,
        source_instrument_identifier=mapping.source_instrument_identifier,
        instrument_id=mapping.instrument_id,
        effective_from=mapping.effective_from,
        effective_to=mapping.effective_to,
        decision_source=mapping.decision_source,
        status=mapping.status.value,
        created_at_utc=mapping.created_at_utc,
    )


def _corporate_action_response(action: CorporateAction) -> CorporateActionResponse:
    return CorporateActionResponse(
        event_id=action.event_id,
        instrument_id=action.instrument_id,
        event_type=action.event_type,
        effective_date=action.effective_date,
        announcement_date=action.announcement_date,
        status=action.status,
        source_name=action.source_name,
        source_reference=action.source_reference,
        payload=json.loads(action.payload_json),
        supersedes_event_id=action.supersedes_event_id,
        created_at_utc=action.created_at_utc,
    )


@v1_instruments_router.post(
    "/instruments", response_model=InstrumentResponse, status_code=status.HTTP_201_CREATED
)
def create_instrument_endpoint(
    payload: CreateInstrumentRequest, settings: Settings = Depends(get_settings)
) -> InstrumentResponse:
    repository = DuckDBInstrumentRepository(settings)
    instrument = create_instrument(
        repository,
        instrument_type=payload.instrument_type,
        display_name=payload.display_name,
        source_name=payload.source_name,
        status=payload.status,
        currency=payload.currency,
        source_reference=payload.source_reference,
    )
    return _instrument_response(instrument)


@v1_instruments_router.get("/instruments", response_model=InstrumentListResponse)
def list_instruments(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> InstrumentListResponse:
    page = DuckDBInstrumentRepository(settings).list(limit=limit, offset=offset)
    return InstrumentListResponse(
        items=[_instrument_response(instrument) for instrument in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@v1_instruments_router.get("/instruments/{instrument_id}", response_model=InstrumentDetailResponse)
def get_instrument(
    instrument_id: str, settings: Settings = Depends(get_settings)
) -> InstrumentDetailResponse:
    instrument = DuckDBInstrumentRepository(settings).get(instrument_id)
    if instrument is None:
        raise NotFoundError()

    aliases = DuckDBInstrumentAliasRepository(settings).list_for_instrument(instrument_id)
    mappings = DuckDBDatasetInstrumentMappingRepository(settings).list_for_instrument(instrument_id)
    corporate_action_page = DuckDBCorporateActionRepository(settings).list_for_instrument(
        instrument_id, limit=1, offset=0
    )

    return InstrumentDetailResponse(
        **_instrument_response(instrument).model_dump(),
        aliases=[_alias_response(alias) for alias in aliases],
        mappings=[
            MappingSummary(
                mapping_id=mapping.mapping_id,
                dataset_id=mapping.dataset_id,
                source_instrument_identifier=mapping.source_instrument_identifier,
                effective_from=mapping.effective_from,
                effective_to=mapping.effective_to,
            )
            for mapping in mappings
        ],
        corporate_action_count=corporate_action_page.total,
    )


@v1_instruments_router.post(
    "/instruments/{instrument_id}/aliases",
    response_model=AliasResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_alias(
    instrument_id: str,
    payload: AddAliasRequest,
    settings: Settings = Depends(get_settings),
) -> AliasResponse:
    try:
        alias = add_instrument_alias(
            DuckDBInstrumentAliasRepository(settings),
            DuckDBInstrumentRepository(settings),
            instrument_id=instrument_id,
            symbol=payload.symbol,
            exchange_code=payload.exchange_code,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            source_name=payload.source_name,
            source_reference=payload.source_reference,
            confidence=payload.confidence,
        )
    except InstrumentNotFoundError as exc:
        raise NotFoundError() from exc
    except AliasOverlapError as exc:
        raise ConflictError(
            details=[{"symbol": exc.symbol, "exchange_code": exc.exchange_code}]
        ) from exc
    return _alias_response(alias)


@v1_instruments_router.post(
    "/datasets/{dataset_id}/instrument-mappings",
    response_model=MappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_instrument_mapping(
    dataset_id: str,
    payload: CreateMappingRequest,
    settings: Settings = Depends(get_settings),
) -> MappingResponse:
    try:
        mapping = create_dataset_instrument_mapping(
            DuckDBDatasetInstrumentMappingRepository(settings),
            DuckDBDatasetRepository(settings),
            DuckDBInstrumentRepository(settings),
            dataset_id=dataset_id,
            source_instrument_identifier=payload.source_instrument_identifier,
            instrument_id=payload.instrument_id,
            effective_from=payload.effective_from,
            decision_source=payload.decision_source,
            effective_to=payload.effective_to,
        )
    except (DatasetNotFoundError, InstrumentNotFoundError) as exc:
        raise NotFoundError() from exc
    except MappingOverlapError as exc:
        raise ConflictError(
            details=[
                {
                    "dataset_id": exc.dataset_id,
                    "source_instrument_identifier": exc.source_instrument_identifier,
                }
            ]
        ) from exc
    return _mapping_response(mapping)


@v1_instruments_router.get(
    "/datasets/{dataset_id}/instrument-mappings", response_model=DatasetMappingListResponse
)
def list_dataset_instrument_mappings(
    dataset_id: str, settings: Settings = Depends(get_settings)
) -> DatasetMappingListResponse:
    if DuckDBDatasetRepository(settings).get(dataset_id) is None:
        raise NotFoundError()

    mappings = DuckDBDatasetInstrumentMappingRepository(settings).list_for_dataset(dataset_id)
    return DatasetMappingListResponse(items=[_mapping_response(mapping) for mapping in mappings])


@v1_instruments_router.post(
    "/instruments/{instrument_id}/corporate-actions",
    response_model=CorporateActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_corporate_action(
    instrument_id: str,
    payload: RecordCorporateActionRequest,
    settings: Settings = Depends(get_settings),
) -> CorporateActionResponse:
    try:
        action = record_corporate_action(
            DuckDBCorporateActionRepository(settings),
            DuckDBInstrumentRepository(settings),
            instrument_id=instrument_id,
            event_type=payload.event_type,
            effective_date=payload.effective_date,
            source_name=payload.source_name,
            payload_json=json.dumps(payload.payload, sort_keys=True),
            status=payload.status,
            announcement_date=payload.announcement_date,
            source_reference=payload.source_reference,
            supersedes_event_id=payload.supersedes_event_id,
        )
    except (InstrumentNotFoundError, CorporateActionNotFoundError) as exc:
        raise NotFoundError() from exc
    return _corporate_action_response(action)


@v1_instruments_router.get(
    "/instruments/{instrument_id}/corporate-actions", response_model=CorporateActionListResponse
)
def list_corporate_actions(
    instrument_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
) -> CorporateActionListResponse:
    if DuckDBInstrumentRepository(settings).get(instrument_id) is None:
        raise NotFoundError()

    page = DuckDBCorporateActionRepository(settings).list_for_instrument(
        instrument_id, limit=limit, offset=offset
    )
    return CorporateActionListResponse(
        items=[_corporate_action_response(action) for action in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
