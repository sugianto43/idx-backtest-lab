# TASK-018 — Remove manual CSV import; Yahoo Finance ticker import is the sole path

## Objective

Remove the manual CSV-upload dataset-creation path (`POST /api/v1/datasets:import` and the `/datasets/import` upload form) entirely, per explicit user request. `POST /api/v1/datasets:import-from-yahoo-finance` (ticker + date range) becomes the only way to create a dataset. This reverses part of ADR-003's original provider-neutral ingestion decision, so it is recorded in a new ADR-011 rather than changed silently.

## Required reading

Read `.claude/CLAUDE.md`, `docs/adr/ADR-003-provider-neutral-local-csv-ingestion.md`, `docs/adr/ADR-010-yahoo-finance-market-data-provider.md`, `docs/CSV_INGESTION_CONTRACT.md`, and this task.

## Dependencies

TASK-016 (Yahoo Finance import) must be complete (it is) — this task removes the alternative path it was added alongside.

## In scope

- `backend/app/api/routes/datasets.py`: remove the `import_dataset` route, `UploadTooLargeError`, and unused `File`/`Form`/`UploadFile`/`InstrumentMappingPolicy` imports. Keep `_build_use_case`, `_get_use_case`, `_import_response_or_raise`, and the Yahoo Finance route unchanged — they're shared/still used.
- `frontend/app/datasets/import/page.tsx`: replace the multipart CSV upload form with a Yahoo Finance ticker form (ticker, instrument identifier, name, start/end date, instrument mapping policy, allow-reimport), calling the existing Yahoo Finance import endpoint.
- `frontend/lib/api/datasets.ts`: replace `importDataset`/`ImportDatasetFields` (multipart) with `importDatasetFromYahooFinance`/`ImportFromYahooFinanceFields` (JSON).
- `frontend/app/page.tsx`: update the "Import a dataset" step description to no longer mention CSV upload.
- `backend/tests/conftest.py` (new): a shared `seed_dataset` helper that seeds a dataset directly through `ImportDatasetUseCase` (bypassing HTTP), since fixtures across multiple test files previously seeded through the now-removed endpoint and never depended on it being reachable over HTTP.
- Update `test_datasets_api.py`, `test_run_artifacts_api.py`, `test_backtest_run_execute_api.py`, `test_backtest_runs_api.py`, `test_instruments_api.py`, `test_optimizations_api.py` to use `seed_dataset` instead of posting to the removed endpoint. CSV-contract-violation and reimport-conflict behavior tests already exist independently at the service layer in `test_dataset_import_service.py` and are unaffected.
- `docs/adr/ADR-011-remove-manual-csv-import.md` (new): records the decision, why it reverses part of ADR-003, and what stays (the CSV contract and validation pipeline remain internal to the Yahoo Finance adapter).
- `docs/adr/ADR-003-provider-neutral-local-csv-ingestion.md`: status line updated to note partial supersession by ADR-011.
- `docs/CSV_INGESTION_CONTRACT.md`: add a note that this is now an internal contract (Yahoo adapter → import use case), not a user-facing upload format.
- `backend/README.md`: update the "Dataset import" section to describe only the Yahoo Finance endpoint.

## Out of scope

- Any change to `ImportDatasetUseCase`, `DelimitedCsvParser`, or the CSV validation rules themselves — only the HTTP surface for user-supplied files is removed.
- Adding any new provider or strategy feature (tracked separately).
- Historical task files (TASK-004, TASK-010, TASK-016) are not rewritten — they're a record of what was true when written.

## Test plan

1. Backend: `pytest` — full suite passes with the CSV-upload-specific HTTP tests removed/replaced, service-layer CSV validation tests untouched and still passing, Yahoo Finance endpoint tests untouched and still passing.
2. Frontend: `npm run test` — `/datasets/import` page tests rewritten for the ticker form and passing; no test anywhere still imports/mocks the removed `importDataset` function.
3. Lint/format/type-check/build (both backend and frontend) pass.
4. Manual: confirm `GET /api/v1/openapi.json` (or route listing) no longer lists `POST /api/v1/datasets:import`.

## Acceptance criteria

- No code path accepts a user-supplied CSV file over HTTP.
- Creating a dataset is possible only via ticker + date range through Yahoo Finance.
- All quality checks pass; ADR-011 records the decision and its scope.

## Definition of done and handoff

After verification, update `.claude/PROJECT_MEMORY.md` and `.claude/TASK_INDEX.md`, and record: the removed endpoint/route, the new `seed_dataset` test fixture pattern and why it exists, ADR-011's key point (CSV contract stays internal; only the upload HTTP surface is gone), and command/test results.

## Next task boundary

TASK-019 (additional strategy kinds) and TASK-020 (picker-based creation UX) are separate, larger follow-ups from the same user request and are tracked as their own tasks.
