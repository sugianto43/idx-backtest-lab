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

_To be completed by the implementing agent after verification._

- Migration version/tables:
- Upload limit and duplicate policy:
- Changes:
- Commands/tests run:
- Results:
- Assumptions/adaptations:
- Risks/follow-up:

## Next task boundary

TASK-005 adds stable instruments, ticker history, corporate-action modeling, and IDX calendar/session decisions. TASK-004 preserves raw identifiers and explicit adjustment status; it must not infer any of those later concepts.
