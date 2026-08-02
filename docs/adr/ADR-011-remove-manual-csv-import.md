# ADR-011: Remove the manual CSV upload endpoint; Yahoo Finance ticker import is the sole ingestion path

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

ADR-003 established a provider-neutral, researcher-supplied CSV upload (`POST /api/v1/datasets:import`) as the first ingestion path, deliberately deferring any specific provider until one was chosen. ADR-010 then added Yahoo Finance ticker-based import (`POST /api/v1/datasets:import-from-yahoo-finance`) as a second path, reusing the same validated CSV contract and import use case internally.

The user, after using the app, asked to remove the manual CSV upload feature entirely and rely only on ticker-based Yahoo Finance import — explicitly choosing simplicity and a single, guided data-entry path over ADR-003's original provider-neutral flexibility. This is a deliberate reversal of ADR-003's ingestion-path decision, not an oversight, so it is recorded as its own ADR per the project's rule that architectural decisions are not silently changed.

## Decision

Remove `POST /api/v1/datasets:import` (multipart file upload) and its frontend form entirely. `POST /api/v1/datasets:import-from-yahoo-finance` (ticker + date range) becomes the only user-facing way to create a dataset. The frontend `/datasets/import` route is repurposed as the Yahoo Finance ticker form (no new route added).

The internal CSV ingestion contract (`docs/CSV_INGESTION_CONTRACT.md`) and the `ImportDatasetUseCase`/`DelimitedCsvParser` pipeline are **not** removed — the Yahoo Finance adapter still converts fetched bars into that exact byte format and feeds them through the same validated, provenanced import path (per ADR-010). Only the HTTP surface that let a user hand-supply arbitrary CSV bytes is removed, along with the `UploadFile`/`multipart` handling in `app/api/routes/datasets.py`.

Backend tests that previously seeded a dataset via the removed HTTP endpoint now call the import use case directly (`backend/tests/conftest.py::seed_dataset`), since seeding test fixtures never depended on the HTTP layer being reachable — only on a dataset existing in the database.

## Consequences

- A user can no longer import their own CSV export, scraped data, or a provider other than Yahoo Finance without writing code — this trades ADR-003's flexibility for a simpler, single guided path, consistent with the product's local-first, single-user, non-commercial scope.
- All datasets in the product now inherit Yahoo Finance's Terms-of-Service constraint (personal, non-commercial use only, per ADR-010) — there is no longer a manual-upload escape hatch for data with different licensing.
- `docs/CSV_INGESTION_CONTRACT.md` is now purely an internal contract between the Yahoo Finance adapter and the import use case, not a user-facing file-format document; its introduction should be read with that in mind.
- Re-adding a second provider or a manual upload path later requires its own ADR, exactly as ADR-003 originally required for any provider beyond the neutral CSV path.

## Reversibility

Moderate. The removed endpoint's logic is fully preserved in `ImportDatasetUseCase` and covered by `backend/tests/test_dataset_import_service.py`; restoring the HTTP route and frontend form is a small, additive change. What is not easily reversible is user expectation — once a manual-upload capability is removed from the product, users who relied on it must be told to use Yahoo Finance or wait for it to be reintroduced.
