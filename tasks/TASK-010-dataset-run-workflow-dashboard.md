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

- Routes/components and API contracts consumed:
- Import/error/retry behavior:
- Warning/unavailable presentation behavior:
- Accessibility/responsive checks:
- Commands/tests and results:
- Deferred charts/comparisons/strategy/run-creation work:

## Next task boundary

TASK-011 adds strategy authoring and validation UX. It may reuse dataset/run selection patterns but must not add arbitrary executable strategy code or expand the backend strategy contract without an ADR.
