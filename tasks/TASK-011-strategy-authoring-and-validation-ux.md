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

- Routes/components/API calls:
- Client validation and backend-error behavior:
- Accessibility/responsive evidence:
- Commands/tests and results:
- Explicitly deferred run creation/strategy capabilities:

## Next task boundary

TASK-012 introduces controlled parameter optimization and bias safeguards. It must use these immutable strategy specifications rather than adding unversioned/free-form browser strategy behavior.
