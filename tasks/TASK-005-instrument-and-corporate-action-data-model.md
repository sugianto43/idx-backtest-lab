# TASK-005 — Instrument and corporate-action data model

## Objective

Add durable instrument identity, effective-dated ticker aliases, and immutable corporate-action evidence. Resolve eligible imported source identifiers to instruments without mutating raw dataset history or adjusting market data.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/ARCHITECTURE_RULES.md`, `docs/DATA_GOVERNANCE.md`, `docs/INSTRUMENT_AND_CORPORATE_ACTION_CONTRACT.md`, ADR-002 through ADR-004, TASK-004, and this task.

## Dependencies

TASK-001 through TASK-004 are complete and verified. Preserve TASK-004 dataset provenance, raw source identifiers, normalized bars, warning behavior, and immutable persistence conventions.

## In scope

- New migrations/tables/repository ports/domain values for instruments, ticker aliases, mapping decisions, and corporate-action records.
- API operations to create/list/get instruments, add aliases/mapping decisions, import/create corporate-action evidence, and inspect each record’s provenance/status.
- A controlled mapping workflow that links a dataset source identifier to an instrument only for a declared effective range.
- Validation, audit events, safe error contracts, and offline tests.

## Out of scope

- Provider integrations, ticker lookup/scraping, automatic symbol matching, or a claim that a mapping is exchange-authoritative.
- Altering normalized bars or any existing dataset metadata.
- Price adjustments, share/portfolio adjustments, dividend proceeds, rights valuation, delisting proceeds, backtests, strategies, or metrics.
- UI, authentication, and any multi-user conflict policy.

## Persistence requirements

Implement a new ordered migration with minimal tables consistent with the contract:

- `instruments`: immutable `instrument_id`, type, display name, currency/status where known, provenance, timestamps.
- `instrument_aliases`: immutable/effective-dated symbol aliases, exchange code, date range, source and mapping status/confidence.
- `dataset_instrument_mappings`: immutable mapping decision between dataset source identifier, date range, and resolved instrument; retain decision source, created timestamp, and status.
- `corporate_actions`: immutable event records with type, effective/announcement dates, status, provenance, payload, and optional supersedes event ID.

Enforce non-empty IDs/symbols, supported types/statuses, valid date ranges, one active mapping per source identifier/range, and non-overlap of resolved aliases where the contract requires it. Keep raw `normalized_bars.source_instrument_identifier` unchanged.

## API contract

Use `/api/v1` and the standard error envelope. Exact field schemas must reflect the contract; do not return raw database paths or internal IDs beyond opaque product IDs.

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/instruments` | Create a sourced instrument record. |
| `GET` | `/api/v1/instruments` | Paginated instrument list with aliases/status. |
| `GET` | `/api/v1/instruments/{instrument_id}` | Instrument, aliases, mappings summary, and corporate-action summary. |
| `POST` | `/api/v1/instruments/{instrument_id}/aliases` | Add a sourced effective-dated alias. |
| `POST` | `/api/v1/datasets/{dataset_id}/instrument-mappings` | Record an explicit source-identifier mapping decision. |
| `POST` | `/api/v1/instruments/{instrument_id}/corporate-actions` | Record immutable corporate-action evidence. |
| `GET` | `/api/v1/instruments/{instrument_id}/corporate-actions` | Paginated event history, including superseded records. |

Use `409` with a stable conflict code for overlapping aliases/mappings or immutable-record conflicts. Unknown source identifiers and unresolved mappings must remain visible rather than being guessed.

## Test plan

1. Create and retrieve an instrument with a stable opaque ID and provenance.
2. Valid aliases and non-overlapping date ranges persist; overlapping aliases/mappings conflict safely.
3. A mapping links a dataset source identifier only in its declared date interval, while original normalized bars stay unchanged.
4. Unresolved/ambiguous mappings reject corporate-action attachment and backtest-eligible resolution requests.
5. Every supported corporate-action type validates required structural fields and retains payload/provenance unchanged.
6. Corrections create superseding records; prior events remain queryable.
7. API pagination/error/correlation behavior meets prior contracts and all tests run offline.
8. No test or implementation claims price adjustment, payout, or tradability from an event record.

## Acceptance criteria

- Internal identity and effective-dated aliases follow ADR-004 and never treat tickers as permanent keys.
- Dataset source identifiers can be explicitly resolved with a durable audit record, without source-history mutation.
- Corporate actions are immutable/provenanced facts only; no financial adjustment logic exists.
- Conflicts, unknowns, and ambiguity are visible through stable API errors/statuses.
- All migrations, repository/API tests, type checks, lint/format checks pass offline.
- Handoff documents exactly what is implemented and which interpretations remain deferred.

## Definition of done and handoff

Do not mark complete until all criteria/tests pass. Update project memory and task index with verified facts, then replace these placeholders:

- Migration version/tables:
  - `backend/migrations/0003_add_instruments_and_corporate_actions.sql` (version 3): `instruments` (`instrument_type` CHECK `'equity'` only, `status` CHECK active/suspended/delisted/unknown), `instrument_aliases` (`exchange_code` CHECK `'IDX'` only, `confidence` CHECK confirmed/tentative, FK to `instruments`), `dataset_instrument_mappings` (FK to `datasets` and `instruments`, `status` CHECK `'resolved'` only — the only status this task ever writes; absence of a mapping row *is* "unresolved", not a stored value), `corporate_actions` (FK to `instruments`, self-referential FK `supersedes_event_id → corporate_actions.event_id`, `event_type`/`status` CHECK-constrained per the contract's vocabulary).
- Alias/mapping conflict policy:
  - Both `instrument_aliases` and `dataset_instrument_mappings` reject an overlapping effective-date range (409 `conflict`) for the same `(symbol, exchange_code)` or `(dataset_id, source_instrument_identifier)` respectively. Overlap is computed in Python (`app/domain/date_ranges.py`) after fetching same-key candidate rows — DuckDB has no native range-exclusion constraint. A `None` `effective_to` is treated as open-ended (unbounded future).
- API endpoints and contracts:
  - `POST /api/v1/instruments`, `GET /api/v1/instruments`, `GET /api/v1/instruments/{id}` (includes aliases, dataset-mapping summaries, and corporate-action count), `POST /api/v1/instruments/{id}/aliases`, `POST /api/v1/datasets/{dataset_id}/instrument-mappings`, `POST /api/v1/instruments/{id}/corporate-actions`, `GET /api/v1/instruments/{id}/corporate-actions` (paginated, includes superseded events). All under the standard `/api/v1` envelope; `404 not_found` for unknown instrument/dataset/superseded-event references, `409 conflict` for overlaps, `422 validation_error` for malformed payloads (via Pydantic enum/field validation).
  - `RecordCorporateActionRequest.payload` accepts an arbitrary JSON object (not a pre-escaped string) for API ergonomics; the route serializes it to `payload_json` text via `json.dumps(..., sort_keys=True)` before it reaches the domain/DB layer, and deserializes it back on read.
- Commands/tests run (from `backend/` with `.venv` active):
  - `ruff format --check .` → passed, 81 files already formatted.
  - `ruff check .` → passed, all checks passed.
  - `mypy` (strict) → passed, no issues in 80 source files.
  - `pytest -q` → passed, 148 passed: date-range overlap logic (parametrized, symmetric), domain validation (instrument/alias/mapping/corporate-action), DuckDB repository round-trips + FK enforcement + overlap detection, application-service orchestration with in-memory fakes (not-found and overlap error paths), and full API contract tests (create/get/list instruments, alias add + conflict, mapping create + not-found + conflict, corporate-action record/list/supersede) via a real temporary DuckDB per test.
  - `docker compose build api` → image built successfully (no new dependencies). Standalone `docker run` smoke test: real `curl` `POST /api/v1/instruments` followed by `GET /api/v1/instruments/{id}` against the running container returned the expected instrument with empty `aliases`/`mappings` and `corporate_action_count: 0`.
- Deferred financial treatment and risks:
  - No price/share/quantity adjustment, dividend cashflow, rights valuation, or delisting-proceeds calculation exists anywhere in this task — corporate actions are recorded evidence only, exactly as the contract requires. `ticker_change` events are recorded as ordinary `corporate_actions` rows; this task does **not** auto-create/update `instrument_aliases` from a `ticker_change` event (the contract says a `ticker_change` "creates/updates effective-dated aliases only with source evidence and no overlapping mapping" — implemented as: an operator/caller records the event via `POST .../corporate-actions` *and* separately calls `POST .../aliases` with the same source evidence; no automatic cross-write between the two tables was added, since inferring one from the other without an explicit decision would be exactly the kind of silent assumption `.claude/CLAUDE.md` prohibits). Revisit if a future task wants that automatic linkage.
  - `AliasConfidence` (`confirmed`/`tentative`) is my own minimal, testable reading of the contract's "confidence/status" phrase, since no concrete enum values are specified there; documented here rather than left implicit.

## Next task boundary

TASK-006 defines strategy specifications and backtest configuration manifests. It may reference resolved instrument IDs and declared adjustment policy, but must not invent corporate-action economics not implemented here.
