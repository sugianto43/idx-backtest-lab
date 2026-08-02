# TASK-014 — Backtest run creation and execution UX

## Objective

Close the gap recorded in `RELEASE_NOTES.md`: there is no frontend UI to create or execute a backtest run. Add a `/runs/new` creation form and an execute trigger on `/runs/{run_id}`, reusing the existing `POST /api/v1/backtest-runs` and `POST /api/v1/backtest-runs/{run_id}:execute` endpoints exactly as-is. No backend or execution-semantics changes.

## Required reading

Read `.claude/CLAUDE.md`, `docs/BACKTEST_MANIFEST_CONTRACT.md`, `docs/DATASET_AND_RUN_WORKFLOW_UX_CONTRACT.md`, `docs/STRATEGY_AUTHORING_UX_CONTRACT.md` (for its create-form conventions, since no run-creation UX contract section exists yet), TASK-006, TASK-009, TASK-010, TASK-011, and this task.

## Dependencies

TASK-006, TASK-009, TASK-010, and TASK-011 must be complete and verified (all are).

## In scope

- `/runs/new`: a form collecting exactly the `CreateBacktestRunRequest` v1 contract fields (strategy ID + version, dataset ID, instrument IDs, start/end date, capital amount/currency, position sizing fraction, quantity increment, money scale, annualization basis, risk-free rate). Client-side ergonomic validation only (required fields, positive-integer/decimal-shaped values); backend remains authoritative.
- An "Execute run" action on `/runs/{run_id}` for a run in `created` status, calling the existing execute endpoint and refreshing the detail view afterward — mirroring the pattern already used on `/optimizations/{optimization_id}`.
- Typed API client additions (`lib/api/runs.ts`): `createRun`, `executeRun`.

## Out of scope

- Any change to run creation/execution/validation semantics, manifest fields, or the backend contract.
- Strategy or dataset creation from within this form (both are selected by ID, copied from their own list pages, matching the existing `/optimizations/new` convention).
- Charting, run comparison, or re-running/cloning a run.

## Test plan

1. Form renders labeled fields for every contract field, blocks submission on missing/malformed values client-side without calling the API, and preserves entered values on a server rejection.
2. Valid submission sends exactly the contract payload and routes to the created run's detail page.
3. `/runs/{run_id}` shows an "Execute run" control only while `status === "created"`, calls the execute endpoint, and reflects the resulting status/terminal outcome afterward.
4. Safe error/correlation-ID display for both creation and execution failures, consistent with TASK-009's shared components.
5. Lint/format/type-check/unit/build checks pass.

## Acceptance criteria

- A researcher can create and execute a backtest run entirely from the browser, with the backend remaining authoritative for all validation and execution.
- No financial or execution logic is duplicated client-side.
- All quality checks pass; status/handoff documents record only verified facts.

## Definition of done and handoff

After verification, update project memory/index, `RELEASE_NOTES.md` (remove the now-closed gap), and record:

- Routes/components/API calls added:
- Client validation and backend-error behavior:
- Commands/tests and results:

## Next task boundary

None specific — this closes a documented v1 gap rather than starting a new phase.
