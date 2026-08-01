# TASK-004 — Market-data ingestion, validation, and provenance

## Objective

Implement an offline, provider-neutral CSV ingestion workflow that creates immutable dataset versions, retains provenance, validates normalized OHLCV bars, and returns actionable warnings/errors. It must support research integrity without connecting to any market-data provider.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/ARCHITECTURE_RULES.md`, `.claude/TEST_GUIDE.md`, `docs/DATA_GOVERNANCE.md`, `docs/CSV_INGESTION_CONTRACT.md`, ADR-002, ADR-003, TASK-003, and this task in full.

## Dependencies

TASK-001 through TASK-003 must be completed and verified. Reuse the established API error envelope, correlation IDs, migration framework, dataset repository, and local file/data-path conventions. Adapt only where a completed task documents an incompatibility.

## Scope

### Required behavior

- Accept a local CSV file and required metadata through a versioned API endpoint.
- Enforce the CSV contract exactly; no delimiter/column/timezone/adjustment guessing.
- Create a new dataset version for every accepted import and retain raw file checksum, metadata, import timestamp, validation summary, and warning records.
- Add normalized bar storage linked to its dataset version. Store normalized timestamps, source identifiers, OHLCV decimal/integer-safe values, interval, and original row reference where provided.
- Add an import status/artifact model that distinguishes `pending`, `valid`, `warning`, and `rejected` dataset validation states.
- Return a safe import response and dataset-detail response that make validation state, provenance, coverage, row counts, and warnings visible.

### Forbidden behavior

- Any provider API, scrape, bundled IDX data, credential, automated download, or claim about data completeness.
- Corporate-action adjustment calculations, ticker-history resolution, universe construction, strategy execution, or performance metrics.
- Partial success that silently drops invalid rows. The initial contract rejects the full import on an invalid row.
- Overwriting/deleting a dataset version or raw import evidence.

## Data model extension

Use a new ordered migration. Keep the existing `datasets` table as version metadata; extend it only via a new migration if necessary. Add the smallest justified tables:

| Table | Minimum content |
| --- | --- |
| `normalized_bars` | dataset ID, source instrument identifier, normalized UTC timestamp, exchange/session representation as available, interval, OHLC decimal-safe values, non-negative volume, source row ID, and a uniqueness constraint. |
| `dataset_validation_events` | immutable event ID, dataset ID/import attempt reference, severity (`warning`/`error`), stable code, safe message, optional source row number, and created UTC timestamp. |
| `dataset_imports` | immutable import ID, dataset ID if created, raw filename sanitized for display, content checksum, byte size, requested metadata, status, counts, started/finished UTC timestamps, and safe failure code. |

Do not store full raw CSV content in DuckDB unless the completed TASK-003 conventions already select a controlled raw-file store. Store a controlled filesystem reference/checksum or equivalent provenance pointer without exposing absolute paths through APIs.

## Application boundaries

- The API layer streams/uploads and validates transport size/content type, then calls an application use case.
- The application use case coordinates raw-file staging, parsing, validation, dataset version allocation, and atomic persistence outcome.
- A CSV parser/normalizer adapter owns file encoding/column parsing and returns product-neutral row values/errors.
- Domain/application validation owns timestamp semantics, OHLC/volume invariants, duplicate detection, and warning/error classification.
- Repositories persist metadata, bars, and immutable validation events; they do not parse CSV.

Set a documented conservative upload size limit. Reject oversized/non-UTF-8/malformed uploads safely and remove temporary staging data according to a tested cleanup policy.

## API contract

Implement, document, and contract-test only:

| Method | Path | Behavior |
| --- | --- | --- |
| `POST` | `/api/v1/datasets:import` | Multipart file plus required metadata. Returns `201` for accepted `valid`/`warning` imports or documented safe `4xx` for rejected requests. |
| `GET` | `/api/v1/datasets/{dataset_id}` | Returns immutable dataset provenance, validation state/summary, coverage, counts, and warnings. |
| `GET` | `/api/v1/datasets` | Paginated metadata list; never returns all bars or raw files. |

Use the standard error envelope. Make dataset IDs opaque. Do not expose filesystem paths, raw untrusted content, provider credentials, or internal stack traces.

## Validation and warning policy

- Contract violations (missing/extra columns, wrong encoding, invalid decimal/time, OHLC invariant violation, duplicate key, mixed interval, unsorted rows) reject the complete import with a stable validation error and safe row reference.
- `adjustment_policy=unknown`, zero-volume bars, absent currency, or warnings explicitly defined by the contract yield a successful dataset with `warning` status and immutable warning events.
- A checksum equal to an existing raw file does not overwrite anything. Create a new version only if the request explicitly allows re-import; otherwise return a safe conflict response and point to the existing dataset ID when permitted.
- Never label data as IDX-validated, adjusted, complete, or tradable unless a specific verified rule has established it.

## Test plan

Create small, human-auditable synthetic fixtures and test:

1. A valid daily CSV creates a dataset, normalized bars, provenance/checksum, correct coverage/counts, and `valid` status.
2. An `unknown` adjustment policy and zero volume create visible warning events/status without changing bar values.
3. Each contract violation rejects the complete import and leaves no usable bars/dataset version.
4. Duplicate rows, incorrect OHLC ordering, invalid numeric values, invalid/non-monotonic timestamps, mixed intervals, unsupported encoding, and extra columns fail safely.
5. Identical imports follow the documented duplicate-check policy; no mutable overwrite occurs.
6. Dataset detail/list responses respect contracts, pagination, and do not expose raw paths/content.
7. Temporary files are cleaned up after success and failure.
8. Parser/domain tests run offline and API tests preserve correlation/error behavior from TASK-002.
9. Migration and repository tests confirm normalized-bar constraints and immutable event persistence.

## Acceptance criteria

- ADR-003 and `CSV_INGESTION_CONTRACT.md` are followed exactly and implementation documentation records any narrow verified clarification.
- Every accepted dataset has immutable source/provenance metadata, checksum, validation state, and auditable warnings.
- Invalid input fails closed; no partial/guessed financial data becomes usable.
- Normalized bars are separated from raw evidence and linked to a versioned dataset.
- API clients can import, list, and inspect a dataset without exposing sensitive internals.
- Full backend migration/repository/API/quality test suite passes offline.
- Task memory/index/handoff records only completed, verified behavior.

## Definition of done

Do not mark complete until all acceptance criteria and tests pass. Update project memory, the task index, API/CSV docs if implementation facts warrant it, and the handoff notes with exact commands/results.

## Handoff notes

- Migration version/tables:
  - `backend/migrations/0002_add_market_data_ingestion.sql` (version 2): `ALTER TABLE datasets ADD COLUMN instrument_mapping_policy` (nullable, default `'ticker_as_of_import'`); new tables `normalized_bars` (DECIMAL(18,6) OHLC, BIGINT volume, FK to `datasets`, UNIQUE on `(dataset_id, source_instrument_identifier, timestamp_utc, bar_interval)`, CHECK constraints for positivity/OHLC relationship/non-negative volume), `dataset_imports` (FK to `datasets`, nullable for rejected imports; `status` reuses the `datasets.validation_status` vocabulary), `dataset_validation_events` (FK to `dataset_imports`, nullable FK to `datasets`).
- Upload limit and duplicate policy:
  - Max upload size: 10 MiB (`MAX_UPLOAD_BYTES` in `app/application/dataset_import_service.py`; also pre-checked in the API route for a fast 413 before reading further). Duplicate policy: SHA-256 of the raw uploaded bytes is looked up against prior *accepted* (`valid`/`warning`) imports; a match returns `409 conflict` with `details[0].existing_dataset_id` unless the caller sets `allow_reimport=true`, in which case a brand-new dataset/version is created from the same bytes.
- Changes:
  - Domain: `app/domain/dataset.py` gained `InstrumentMappingPolicy` enum and a new `DatasetManifest.instrument_mapping_policy` field (defaulted to `TICKER_AS_OF_IMPORT` so existing TASK-003 call sites keep compiling). `app/domain/market_data.py` (new): `NormalizedBar`, `ValidationSeverity`, `DatasetValidationEvent`, `DatasetImport` — all validated, framework-independent dataclasses.
  - CSV parsing: `app/application/ports/csv_parser.py` defines the `CsvParser` Protocol plus the `ParsedRow`/`ParsedImport` DTOs (kept in application, not infrastructure, so application code never imports infrastructure directly). `app/infrastructure/ingestion/csv_parser.py` implements the actual parsing/normalization (`DelimitedCsvParser`) and raises `app.application.errors.CsvContractViolation` (code + safe message + optional 1-indexed row number, header row counted).
  - Application: `app/application/dataset_import_service.py` (`ImportDatasetUseCase`) orchestrates validate-metadata → size-check → duplicate-check → parse → build warnings → persist. `app/application/errors.py` gained `CsvContractViolation` and `DatasetReimportConflictError`. New ports: `dataset_import_repository.py` (`get`, `find_by_content_checksum`, `get_latest_for_dataset`), `dataset_import_writer.py` (`persist_accepted_import`, `persist_rejected_import` — the atomic multi-table write boundary).
  - Infrastructure: `app/infrastructure/db/dataset_import_writer.py` (`DuckDBDatasetImportWriter`) does the accepted-path write (`datasets` + `normalized_bars` + `dataset_imports` + warning `dataset_validation_events`) and the rejected-path write (`dataset_imports` + one error event) each inside one `BEGIN/COMMIT`, with `ROLLBACK` on any exception. `app/infrastructure/db/dataset_import_repository.py` and `dataset_validation_event_repository.py` are read repositories. `app/infrastructure/db/dataset_repository.py` was extended (not replaced) for the new `instrument_mapping_policy` column.
  - API: `app/api/routes/datasets.py` — `POST /api/v1/datasets:import`, `GET /api/v1/datasets/{dataset_id}`, `GET /api/v1/datasets`; `app/api/schemas/datasets.py`. New error types in the route module: `UploadTooLargeError` (413 `payload_too_large`), `DatasetImportRejectedError` (422 `validation_error`, details carry the specific contract-violation code + row number), `DatasetConflictError` (409 `conflict`).
- Commands/tests run (from `backend/` with `.venv` active):
  - `ruff format --check .` → passed, 59 files already formatted.
  - `ruff check .` → passed (added `fastapi.File`/`fastapi.Form` to `flake8-bugbear`'s `extend-immutable-calls` in `pyproject.toml`, same rationale as `Depends`/`Query` from TASK-002).
  - `mypy` (strict) → passed, no issues in 58 source files.
  - `pytest -q` → passed, 95 passed: CSV parser (valid daily/intraday parsing, every contract-violation code, row-number reporting, optional columns), domain validation (bars/events/import records), use-case orchestration with in-memory fakes (valid/warning/rejected paths, upload-too-large, invalid metadata, reimport conflict with and without `allow_reimport`), DuckDB writer integration (accepted/rejected writes, transactional rollback on a forced constraint violation), and full API contract tests (201/422/409/404/200, pagination) via a real temporary DuckDB per test.
  - `docker compose build api` → image built successfully (added `python-multipart` — required by FastAPI for `File`/`Form` — to `requirements.txt`). Standalone `docker run` smoke test: a real `curl -F` multipart upload against the running container returned `201` with a real `dataset_id`, proving genuine end-to-end behavior (not just mocked tests).
- Results: all above commands passed with no known failures.
- Assumptions/adaptations:
  - DuckDB 1.5.5 does not support `ALTER TABLE ... ADD COLUMN ... NOT NULL` or `ALTER TABLE ... ADD CONSTRAINT` (verified empirically — both raise `Parser Error` / `Not implemented Error`). `datasets.instrument_mapping_policy` is therefore a nullable column with a SQL-level `DEFAULT`; the required/allowed-values invariant is enforced in `DatasetManifest.__post_init__` instead (the documented fallback for exactly this situation).
  - DuckDB 1.5.5 *does* enforce `FOREIGN KEY` constraints and supports `DECIMAL(18,6)` round-tripping cleanly to/from Python's `decimal.Decimal` (both verified empirically) — used for OHLC prices instead of VARCHAR, giving exact decimal storage.
  - "Mixed interval" rejection (listed in the task's test-plan wording) has no realizable meaning under the current CSV contract: `bar_interval` is a single declared upload-metadata value for the whole file, not a per-row CSV column, so there is nothing that could literally be "mixed" within one conformant file. No such check or test was invented; this is flagged in `PROJECT_MEMORY.md` as an open ambiguity rather than silently assumed away.
  - The instrument-identifier-to-instrument resolution implied by `instrument_mapping_policy` is recorded as declared metadata only; no resolution logic exists yet (explicitly deferred to TASK-005, per the task's own scope boundary).
- Risks/follow-up:
  - Raw uploaded file bytes are not separately persisted to a controlled file store (only their SHA-256 checksum and byte size are recorded) — TASK-003's conventions did not select a raw-file store, and the task explicitly allows checksum/reference-only provenance in that case. Revisit if a future task needs to re-serve the original file.
  - `dataset_imports.content_checksum` lookups scan by checksum without an index beyond the primary key; acceptable at current scale, worth an index if import volume grows.

## Next task boundary

TASK-005 adds stable instruments, ticker history, corporate-action modeling, and IDX calendar/session decisions. TASK-004 preserves raw identifiers and explicit adjustment status; it must not infer any of those later concepts.
