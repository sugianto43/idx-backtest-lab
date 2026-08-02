# TASK-016 — Yahoo Finance market data import

## Objective

Close the "no market-data provider integration" limitation recorded in `RELEASE_NOTES.md`, per the user's explicit choice of Yahoo Finance as the first provider. Add a thin adapter that fetches daily OHLCV history from Yahoo Finance's public chart endpoint, converts it into the existing CSV ingestion contract format, and imports it through the *existing, unmodified* dataset-import pipeline. No new ingestion, validation, or persistence logic.

## Required reading

Read `.claude/CLAUDE.md`, `docs/DATA_GOVERNANCE.md`, `docs/CSV_INGESTION_CONTRACT.md`, `docs/adr/ADR-003-provider-neutral-local-csv-ingestion.md`, `docs/adr/ADR-010-yahoo-finance-market-data-provider.md`, TASK-004, and this task.

## Dependencies

TASK-004 (market-data ingestion) must be complete and verified (it is).

## In scope

- `app/infrastructure/market_data/yahoo_finance_provider.py`: fetches daily OHLCV for one ticker over a date range from Yahoo's public chart JSON endpoint using only the Python standard library (`urllib.request`, `json`) — no new third-party dependency. Converts the response into exact CSV_INGESTION_CONTRACT bytes (`timestamp,instrument_identifier,open,high,low,close,volume`), using Yahoo's split-adjusted `close` and tagging `adjustment_policy=split_adjusted`.
- `POST /api/v1/datasets:import-from-yahoo-finance`: accepts a ticker, date range, and the same dataset metadata fields the manual import form collects (name, source reference override if any, timezone, instrument_mapping_policy); builds the CSV via the adapter above; calls the existing `ImportDatasetUseCase` exactly as `POST /api/v1/datasets:import` does. `source_name` is fixed to `"Yahoo Finance"` and `license_reference` is fixed to an explicit personal/non-commercial-use citation of Yahoo's Terms of Service — both are never caller-supplied free text for this path, since the true values are already known.
- Network-failure and empty-result handling: a fetch failure or an empty date range is a safe `502`/`422` error, never a fabricated empty-but-successful import.
- Tests using an injected/mocked HTTP fetch function — no real network access in the test suite, matching every prior task's offline-fixture convention.

## Out of scope

- Any frontend UI for this endpoint (the existing `/datasets/import` manual-CSV form is unaffected; a Yahoo Finance import UI is deferred to a follow-up task if wanted).
- Corporate-action, dividend, currency-conversion, or exchange-calendar handling — out of scope exactly as it is for manual CSV import.
- Any other data provider, or making Yahoo Finance the only/default path — manual CSV import remains fully supported and unchanged.
- Scheduled/automatic refresh — this is an on-demand, user-triggered fetch only.

## Test plan

1. The adapter converts a mocked Yahoo chart JSON response into exact, contract-conformant CSV bytes (header, row format, chronological order) — hand-verifiable against a small fixture.
2. The new endpoint calls the existing `ImportDatasetUseCase` with the converted bytes and fixed `source_name`/`license_reference`, and behaves identically to the manual endpoint for validation/warning/rejection/conflict outcomes (proven by asserting the same `dataset_imports`/`normalized_bars` rows result).
3. A Yahoo fetch failure (network error, non-200, malformed JSON, empty series) returns a safe, documented error — never a partial or fabricated dataset.
4. `ruff`/`mypy`/`pytest` all pass; no new dependency was added.

## Acceptance criteria

- A dataset can be created from real Yahoo Finance data through one API call, fully provenanced and indistinguishable in storage from a manually imported dataset with the same content.
- No ingestion/validation logic is duplicated; the CSV contract remains the single source of truth.
- License/provenance fields for this path are accurate and non-editable by the caller.
- All verification passes; status/handoff documents record only verified facts.

## Definition of done and handoff

After verification, update project memory/index, `RELEASE_NOTES.md`, and record:

- Adapter and endpoint added, exact fields fixed vs. caller-supplied: `app/infrastructure/market_data/yahoo_finance_provider.py::fetch_daily_ohlcv_csv` (stdlib-only HTTP fetch + CSV conversion) and `POST /api/v1/datasets:import-from-yahoo-finance` (`ticker`, `instrument_identifier` optional, `start_date`, `end_date`, `name`, `instrument_mapping_policy`, `allow_reimport` are caller-supplied; `source_name`, `license_reference`, `bar_interval`, `timezone`, `adjustment_policy` are fixed by the endpoint, not caller-editable).
- Adjustment-policy and license-reference decisions: `adjustment_policy="split_adjusted"` (Yahoo's plain `close`, not `Adj Close`). `license_reference` is a fixed citation of Yahoo's Terms of Service (personal, non-commercial use only, redistribution prohibited) — see ADR-010 for the full rationale and the hard constraint against commercial/hosted deployment.
- Commands/tests and results: `ruff format --check .`/`ruff check .`/`mypy .`/`pytest -q` all clean, 289 passed (9 new). `docker compose build api` succeeds; a live smoke test made a real network call to Yahoo Finance for `AAPL` and correctly imported 6 real trading bars with the expected fixed provenance.
- Deferred frontend UI: Not built in this task; `/datasets/import` (manual CSV) is unaffected. A "Import from Yahoo Finance" form is a natural follow-up if wanted.

## Next task boundary

A frontend "import from Yahoo Finance" UI on `/datasets/import` is a natural, optional follow-up but is not required by this task.
