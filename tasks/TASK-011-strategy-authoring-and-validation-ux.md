# TASK-011 — Strategy authoring and validation UX

## Objective

Replace the strategy placeholder with accessible create/list/detail UI for the validated declarative strategy specification v1. Users can author only the `sma_crossover` contract and inspect its immutable versions; the UI does not execute or evaluate strategy logic.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/CODING_STANDARDS.md`, `docs/BACKTEST_MANIFEST_CONTRACT.md`, `docs/FRONTEND_FOUNDATION_CONTRACT.md`, `docs/STRATEGY_AUTHORING_UX_CONTRACT.md`, ADR-005, ADR-008, TASK-006, TASK-009, TASK-010, and this task.

## Dependencies

TASK-006, TASK-009, and TASK-010 must be complete and verified. The backend strategy create/list/get endpoints and typed frontend API client must exist. Do not hide missing API capabilities behind mock success behavior.

## In scope

- Strategy list, creation, and immutable version-detail routes/components.
- Typed API-client models/calls for documented strategy endpoints.
- Client-side ergonomic validation that mirrors—but never replaces—backend validation.
- Plain-language explanation of strategy and manifest timing semantics.
- Tests for rendering, input/error handling, typed API interaction, accessibility, and responsive behavior.

## Out of scope

- New strategy kinds/parameters, custom code/script editor, indicator calculations, signal preview, historical-data preview, charting, backtest-run creation/execution, optimizer, strategy edit/delete/clone, browser persistence, or performance claims.
- Backend strategy-contract changes unless a completed-contract defect requires a separately documented scoped change.

## Implementation requirements

- Reuse TASK-009 API client/error/status components and TASK-010 responsive table/pagination patterns.
- Form input types and parsing must preserve integer semantics; reject decimal/scientific/unsafe values before display/submission while allowing backend to remain authoritative.
- Make required/immutable/read-only fields unambiguous. Do not present hidden defaults as user choices.
- Explain `fast_window < slow_window`, close-based signal evaluation, warm-up eligibility, long-only behavior, and next-bar-open execution relationship in concise accessible copy.
- On success, use API-returned ID/version/checksum; do not compute a client checksum.
- Show API validation/conflict errors with field association when details are safe and known; otherwise show a safe summary plus correlation ID.
- Strategy list/detail uses backend pagination/order. Never sort/rank strategy by outcome or infer latest version beyond API-provided fields.

## Test plan

1. List supports loading, empty, error, unavailable, paginated success, long names/IDs, and keyboard navigation.
2. Create form provides labels/help/required state, valid values, invalid integers, `fast_window >= slow_window`, missing name, server validation, conflict, network, and malformed-response behavior.
3. Valid submission sends exactly v1 contract payload and routes to API-returned immutable detail.
4. Detail renders returned kind, parameters, policy, version, checksum, timestamp, and plain-language semantics without editable controls.
5. Tests prove no client indicator/SMA computation, historical data fetch, executable strategy evaluation, or financial-performance display exists.
6. Focus management, live error announcements, contrast/non-color validation, narrow viewport behavior, lint/format/type/component/build checks pass.

## Acceptance criteria

- UI adheres exactly to the strategy v1 and UX contracts.
- A researcher can create/inspect strategy versions while understanding their limited deterministic semantics.
- Validation is accessible, safe, and backend-authoritative; error/correlation handling is consistent.
- The UI makes no claims about performance/execution and performs no strategy/financial calculation.
- All quality checks pass and status/handoff documents record verified facts only.

## Definition of done and handoff

After verification, update project memory/index and record:

- Routes/components/API calls: `/strategies` (list, `GET /api/v1/strategies`), `/strategies/new` (`POST /api/v1/strategies`), `/strategies/{strategy_id}/versions/{version}` (`GET /api/v1/strategies/{id}/versions/{version}`). `lib/api/strategies.ts` (typed models + calls), reuses `components/data/{ProvenanceList,PaginationControls,ResponsiveTable}` and `components/status/*` from TASK-009/010. No backend changes — the existing TASK-006 endpoints already matched the UX contract's routes and fields.
- Client validation and backend-error behavior: Name required; fast/slow window inputs are `type="text"`/`inputMode="numeric"` validated against `/^[1-9]\d*$/` (rejects decimals, scientific notation, leading zeros, non-digits) before parsing to a JS number via `Number.isSafeInteger`; `fast_window < slow_window` checked client-side. All checks block submission before any network call and are explicitly convenience-only. A server rejection preserves every entered field (React state untouched on error) and renders via the shared `ErrorState` (safe message + code + correlation ID).
- Accessibility/responsive evidence: One `<h1>` per route; form inputs have `<label htmlFor>` and `aria-describedby` help text; the fixed signal-policy fields are presented in a `<fieldset>`/`<legend>` as read-only text, never as editable controls; the detail route has zero `<input>`/`<button>` elements (verified by test). Reuses TASK-010's `.responsive-table`/`.id-value` CSS for the list table and checksum display. No automated viewport test (jsdom does not lay out CSS), consistent with prior tasks — verified by SSR HTML inspection via `curl` against a `docker run` container instead.
- Commands/tests and results: Backend — unchanged, `pytest -q` → 245 passed (no backend files touched). Frontend — `npm run format`/`lint`/`type-check` clean, `npm run test` → 70 passed across 19 files (+14 for this task), `npm run build` succeeds (10 routes). `docker compose build web` succeeds; a live two-container smoke test created a real strategy via `curl` against the API container and confirmed `/strategies`, `/strategies/new`, and `/strategies/{id}/versions/{version}` all render their correct SSR shell (list heading, create-form heading, and the version-detail page's initial loading state) against a live backend.
- Explicitly deferred run creation/strategy capabilities: No strategy edit/delete/clone (immutable-only, matches contract). No new-run form or execute trigger from a strategy detail page (still TASK-006/007/008's API-only surface). No signal preview, indicator chart, or historical-data fetch — the detail page only echoes the backend-returned specification and static plain-language semantics text.

## Next task boundary

TASK-012 introduces controlled parameter optimization and bias safeguards. It must use these immutable strategy specifications rather than adding unversioned/free-form browser strategy behavior.
