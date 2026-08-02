# TASK-010 — Dataset/run workflow dashboard

## Objective

Implement an accessible frontend workflow for importing/inspecting datasets and reviewing completed run artifacts. The dashboard must faithfully represent backend status, provenance, warnings, and metric availability without browser-side financial logic.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/AI_AGENT_CONSTITUTION.md`, `docs/API_CONVENTIONS.md`, `docs/CSV_INGESTION_CONTRACT.md`, `docs/RESULT_ARTIFACT_AND_METRIC_CONTRACT.md`, `docs/FRONTEND_FOUNDATION_CONTRACT.md`, `docs/DATASET_AND_RUN_WORKFLOW_UX_CONTRACT.md`, TASK-004, TASK-008, TASK-009, and this task.

## Dependencies

TASK-004, TASK-008, and TASK-009 must be complete and verified. The required dataset/run endpoints and typed API-client foundation must exist. Do not work around missing endpoint fields with client inference; return the change to the owning backend task if a contract is inadequate.

## In scope

- Dataset list/detail/import routes and components.
- Run list/detail routes and artifact/metric/event/snapshot/reproducibility-manifest views.
- Typed API-client extensions and contract fixtures for all consumed endpoints.
- Reusable status, provenance, warning, pagination, structured-manifest, and responsive-table components.
- Browser-side download of the already generated safe reproducibility manifest only.

## Out of scope

- Strategy creation/editor, new-run form/execute trigger, optimizer, charts, comparisons/rankings, authentication, browser persistence, server mutations beyond CSV import, or changes to calculation semantics.
- Rendering raw CSV/data files, database paths, source credentials, raw stack traces, or unbounded event data.
- Any JS math for metrics, P&L, drawdown, annualization, sorting/ranking financial values, or portfolio reconstruction.

## Implementation requirements

- Reuse the TASK-009 typed API client; add complete typed responses/errors for every consumed dataset/run endpoint.
- Keep page/server/client responsibilities narrow. Remote reads and mutations must expose loading/empty/error/unavailable/success states.
- Dataset import form matches the CSV contract exactly, includes explanatory help for adjustment policy/timezone/license fields, enforces file-size/type hints, and does not claim client validation is authoritative.
- Preserve server validation errors safely after an import failure; show row references/messages only as provided by API and never echo arbitrary CSV content.
- Render all backend warnings in each relevant list/detail view. Use a summary count plus expanded accessible details; warnings cannot be hidden solely by a collapsed default control.
- Render metric `available` vs `not_available` and its reason exactly. Format received decimal strings for locale display only with a tested display utility; retain source values and do not do arithmetic.
- Use stable server pagination with explicit next/previous or page controls. Do not request/load every event/snapshot client-side.
- Reproducibility export must retain its backend-provided filename/content type and show what it contains/excludes before download.
- Display the research disclaimer on dashboard views, alongside specific caveats from run/dataset data.

## API requirements

Consume only existing documented endpoints from TASK-004/TASK-008 plus foundation health status. If an endpoint needs a small non-financial presentation field such as pagination cursors, add a contract-first backend change with tests and document it; do not invent values on the client.

## Test plan

1. Dataset list/detail displays all provenance, status, adjustment-policy, warning, loading, empty, error, and pagination states from typed fixtures.
2. Import form sends exactly contract metadata/file, correctly handles `201`, validation, conflict, unavailable/network, and malformed API responses, and never loses safe retry context.
3. Run list/detail displays status, provenance/checksums, manifest, warning detail, metric value/status/reason, events, snapshots, and failed/no-artifact states exactly as API returns.
4. Decimal-string fixtures prove no frontend financial computation; unavailable metric values cannot render as zero or participate in sorting.
5. Reproducibility-manifest download uses safe API content and errors accessibly.
6. Long IDs/checksums, empty lists, pagination, narrow screen behavior, keyboard navigation, table semantics, focus handling, and screen-reader states are covered.
7. Existing frontend lint/format/type/unit/component/build checks pass; API client contracts are mocked/versioned, not dependent on live data.

## Acceptance criteria

- Dataset import/list/detail and run list/detail fulfill the UX contract accessibly and honestly.
- Provenance, adjustment policy, warnings, status, unavailable values, and reproducibility evidence are visible in the primary workflow.
- UI consumes typed API contracts and performs no business/financial calculation or unsupported inference.
- Responses are paginated and errors/correlation IDs are safe/actionable.
- All frontend checks/tests/build pass; handoff/status documents contain verified evidence only.

## Definition of done and handoff

After verification, update project memory/index and complete:

- Routes/components and API contracts consumed: `/datasets` (list, `GET /api/v1/datasets`), `/datasets/import` (`POST /api/v1/datasets:import`), `/datasets/[dataset_id]` (`GET /api/v1/datasets/{id}`), `/runs` (`GET /api/v1/backtest-runs`), `/runs/[run_id]` (`GET /api/v1/backtest-runs/{id}` plus TASK-008's `.../summary`, `.../artifacts`, `.../events?type=`, `.../portfolio-snapshots`, `.../reproducibility-manifest`). Shared: `lib/api/{datasets,runs,run-artifacts}.ts` (typed request/response models), `components/data/{MetricValue,WarningsList,PaginationControls,ProvenanceList,ResponsiveTable}.tsx`, `lib/format/decimal.ts`. Two backend contract additions consumed: `DatasetSummary.row_count`/`warning_count`, `BacktestRunResponse.final_equity`/`total_return`.
- Import/error/retry behavior: Client-side checks (file selected, ≤10 MB, required text fields) block submission before any network call and are explicitly labeled as convenience only. Every field value survives a server-side rejection (React state is never cleared on error) so the user can fix and resubmit without re-entering data. `409 conflict` shows the backend's `existing_dataset_id` (from `error.details`) and points at the "allow re-import" checkbox; other errors render via the shared `ErrorState` (safe message + code + correlation ID, no stack traces).
- Warning/unavailable presentation behavior: `WarningsList` always renders the full list next to its count — never behind a `<details>`/collapsed control. `MetricValue` and the run-list table cells render `not_available` as "Not available (<reason>)", never `0`/blank, and unavailable values are excluded from any implied ordering (the run list is server-ordered by creation time only, never re-sorted client-side). A run with no artifact bundle yet shows a distinct `UnavailableState` ("has not produced result artifacts yet") rather than a generic error, driven by detecting the backend's `404`/`not_found` response.
- Accessibility/responsive checks: One `<h1>` per route; `<section aria-labelledby>` landmarks for each run-detail subsection; tables use `<caption>`, `scope="col"`/`scope="row"`, and a `.responsive-table` horizontal-scroll wrapper (no reliance on wide viewports); long IDs/checksums use a `.id-value` class (`overflow-wrap: anywhere`, monospace) to wrap safely; form inputs have associated `<label>`s and `aria-describedby` help text. Verified by SSR HTML inspection (`curl` against a `docker run` container) and CSS review; no automated viewport/breakpoint test exists (jsdom does not lay out CSS), consistent with the TASK-009 precedent.
- Commands/tests and results: Backend — `ruff format`/`check`, `mypy`, `pytest -q` all clean, 245 passed (was 244; +1 for the new `DatasetSummary` fields, +2 for `final_equity`/`total_return` on create/get). Frontend — `npm run format`/`lint`/`type-check` clean, `npm run test` → 56 passed across 16 files, `npm run build` succeeds (9 routes, 2 dynamic). `docker compose build api web` succeeds; a live two-container smoke test (API + web on a bridge, real dataset import → instrument → mapping → strategy → run → execute via `curl`) confirmed `GET /api/v1/datasets` returns real `row_count`/`warning_count` and `GET /api/v1/backtest-runs` returns real `final_equity`/`total_return` after execution, and the `/datasets`/`/runs` SSR shells render correctly against a live backend.
- Deferred charts/comparisons/strategy/run-creation work: No charting (tables/JSON only, as scoped). No comparison/ranking UI (TASK-008's `comparison-compatibility` endpoint is unused here — deferred, likely TASK-012). No strategy creation/editor or new-run form (`/strategies` remains TASK-009's placeholder). No execute-trigger button on `/runs/{run_id}` — runs must already be executed via the API for their artifacts to appear.

## Next task boundary

TASK-011 adds strategy authoring and validation UX. It may reuse dataset/run selection patterns but must not add arbitrary executable strategy code or expand the backend strategy contract without an ADR.
