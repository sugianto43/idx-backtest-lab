# TASK-012 — Optimization framework with bias safeguards

## Objective

Implement an auditable, deterministic finite-grid optimizer for strategy v1 that uses chronological train/validation/holdout partitions and protects holdout data from selection. Expose research evidence and safeguards, not investment recommendations.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/AI_AGENT_CONSTITUTION.md`, `.claude/TEST_GUIDE.md`, `docs/BACKTEST_MANIFEST_CONTRACT.md`, `docs/ENGINE_EXECUTION_CONTRACT.md`, `docs/RESULT_ARTIFACT_AND_METRIC_CONTRACT.md`, `docs/OPTIMIZATION_AND_BIAS_SAFEGUARD_CONTRACT.md`, ADR-005 through ADR-009, TASK-006 through TASK-011, and this task.

## Dependencies

TASK-008 and TASK-011 must be complete and verified. Valid immutable manifests, deterministic engine runs, artifact metrics, typed frontend foundation, and strategy-authoring UI must exist. This task may need small API/UI extensions but must reuse—not recreate—the underlying run engine/artifact paths.

## In scope

- Immutable optimization manifests/results, migrations, repositories, ports, application orchestration, and safe lifecycle transitions.
- Canonical finite parameter-grid expansion for SMA windows and chronological partition validation.
- Candidate train/validation run creation/execution/artifacts using the existing engine/artifact contracts.
- Selection, tie-break, one-time sealed holdout evaluation, warnings, error behavior, and audit logging.
- API endpoints and an accessible frontend create/list/detail workflow that communicates safeguards and research-only limitations.

## Out of scope

- Random/Bayesian/genetic search, adaptive trials, machine learning, parallel/distributed execution, automatic parameter suggestions, multi-objective scoring, custom objectives, cross-validation shuffle, walk-forward rolling windows, benchmark optimization, strategy code, or trading recommendations.
- Reusing/changing a completed optimization, exposing holdout candidate information during selection, or deleting failed candidates.
- Browser-side objective computation, ranking, or financial calculation.

## Backend design requirements

- Define product-neutral optimization ports/types; engine/persistence details stay in existing infrastructure adapters.
- Persist base input checksums and every materialized candidate/run checksum. Candidate order must be canonical and independent of database insertion/concurrency order.
- Validate partition coverage/eligibility before launching candidates. Reject insufficient/overlap/reversed partitions, unknown metric definition, unavailable objective policy, unsupported strategy/parameter, or data-policy mismatch.
- Enforce an explicit bounded maximum candidate count from typed settings; reject oversized grids before execution and record no partial optimization.
- Use application-owned lifecycle states such as `created`, `validating`, `running_train_validation`, `selecting`, `running_holdout`, `completed`, `failed`, `cancelled`; only documented forward transitions are legal.
- The holdout run must be created only after a selected candidate exists. Access-control/query behavior must keep holdout data absent from candidate-selection responses until terminal selection audit is recorded.
- Candidate failure/unavailable objective does not abort remaining candidates unless a system-level failure makes result integrity impossible; record reason/status deterministically.

## API and UI contract

Implement versioned typed contracts; exact names may follow existing conventions:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/optimizations` | Validate and create immutable optimization manifest. |
| `POST` | `/api/v1/optimizations/{optimization_id}:execute` | Execute once through lifecycle; reject duplicate/concurrent invocation. |
| `GET` | `/api/v1/optimizations` | Paginated optimization summaries/statuses. |
| `GET` | `/api/v1/optimizations/{optimization_id}` | Manifest, lifecycle, selection audit, candidate summary, and holdout-sealed/terminal view. |
| `GET` | `/api/v1/optimizations/{optimization_id}/candidates` | Paginated train/validation candidate records only; no holdout leakage before completion. |

Frontend routes may be `/optimizations`, `/optimizations/new`, and `/optimizations/{optimization_id}`. Creation forms allow only contract-supported grid/partition/objective inputs and display calculated candidate count without ranking/evaluation. Detail presents partitions chronologically, candidate statuses, selection rule, warnings, and research-only disclaimer. Holdout result is visibly sealed until terminal completion.

## Test plan

1. Grid canonicalization, invalid-pair rejection, maximum count limit, manifest checksum, and immutable persistence are deterministic.
2. Partition validation rejects overlap, reversed dates, insufficient warm-up/next-bar coverage, interval/policy mismatch, and unknown objective before any candidate run starts.
3. Candidate order, generated manifest/run references, validation objective ranking, unavailable/failed candidate exclusion, and tie-break exactly follow the contract.
4. Holdout is not created/readable during selection; it executes exactly once for selected candidate and cannot change selection.
5. Every candidate/rejection/failure/warning appears in immutable audit output; no silent retry/drop occurs.
6. Lifecycle tests cover success, duplicate/concurrent execution, expected system failure, cancellation policy, and safe errors/correlation IDs.
7. UI tests cover accessible partition/grid forms, candidate-count constraint, disclaimer, sealed holdout state, unavailable objective, pagination, long run/ID states, and no browser-side calculations.
8. Synthetic offline fixtures demonstrate a tempting overfit candidate selected by validation while holdout is reported separately, without editorializing future performance.
9. Full backend/frontend migration, contract, static, lint, format, type, unit/component, and build suites pass offline.

## Acceptance criteria

- Optimizer follows ADR-009 and safeguard contract exactly; all inputs/results are immutable/checksummed/auditable.
- Validation selection is chronologically isolated from holdout; holdout cannot influence parameter choice.
- Candidate failures/unavailable values and all selection rules are visible, deterministic, and never silently removed.
- UI/API clearly label output as research-only and never give recommendations/predictions.
- No unsupported search algorithm or frontend financial logic is introduced.
- All verification passes and status/handoff contains verified facts only.

## Definition of done and handoff

After verification, update project memory/index and record:

- Optimization schema/settings/candidate limit: Migration `0006_add_optimizations.sql` (`optimizations`, `optimization_candidates`, `OPTIMIZATION_SCHEMA_VERSION = 1`). New typed setting `APP_OPTIMIZATION_MAX_CANDIDATE_COUNT` (default 50) bounds the canonical grid size (valid + rejected pairs together) — checked before any candidate executes; an oversized grid persists no optimization row at all.
- Partition, objective, tie-break, and holdout sealing behavior: Partitions must satisfy `train_end < validation_start <= validation_end < holdout_start <= holdout_end` (checked at creation) and each needs `largest_slow_window + 2` real bars (warm-up + one eligible signal + one next-bar-open fill opportunity), also checked at creation via the real bar snapshot. Objective is one of the 9 TASK-008 metric keys, predeclared and fixed always-maximize (no minimize mode — every v1 metric, including `max_drawdown`, is already oriented higher-is-better, so a fixed rule satisfies the contract without inventing an unspecified minimize option). Tie-break: highest objective value, then lower `slow_window`, then lower `fast_window`, then candidate ID — implemented as a pure function (`app/domain/optimization.py::select_candidate`), unit-tested independent of persistence. Holdout executes exactly once, only for the selected candidate, only after selection is recorded; `GET /api/v1/optimizations/{id}` computes `holdout.sealed = (status != completed)` at the response layer, so holdout fields are unreadable through the API itself (not just hidden by the UI) until terminal completion.
- API/routes and audit fields: `POST /api/v1/optimizations` (create, 422 on invalid grid/partitions/objective/oversized-grid/insufficient-coverage), `POST /api/v1/optimizations/{id}:execute` (409 on duplicate/concurrent execute via the same lifecycle-transition guard pattern as TASK-007/008's backtest runs), `GET /api/v1/optimizations` (paginated summaries), `GET /api/v1/optimizations/{id}` (manifest, lifecycle, sealed-until-completion selection audit + holdout), `GET /api/v1/optimizations/{id}/candidates` (paginated, train/validation only, never holdout). Every candidate — including rejected pairs and failed train/validation runs — is a persisted row with a reason; nothing is silently dropped or retried.
- Commands/tests and results: Backend — `ruff format`/`check`, `mypy`, `pytest -q` all clean, 280 passed (was 245; +35 for domain/repository/API optimization tests, including a synthetic "tempting overfit" fixture per the test plan: a strong validation-window uptrend followed by a holdout-window reversal, proving the holdout run is genuinely independent — its own run ID, never reused from validation). Frontend — `npm run format`/`lint`/`type-check` clean, `npm run test` → 84 passed across 22 files (+14 for this task), `npm run build` succeeds (13 routes). `docker compose build api web` succeeds; a live smoke test via `curl` against the API container ran a full 4-candidate optimization end-to-end (one candidate legitimately failed with `train_run_failed`, three completed, selection made, holdout evaluated once and revealed only post-completion) and confirmed the web container's `/optimizations` and `/optimizations/new` SSR shells render against a live backend. **Real bug found and fixed during implementation:** `optimization_candidates.optimization_id` originally had `REFERENCES optimizations (optimization_id)`; since `optimizations.status` updates repeatedly through the lifecycle and DuckDB implements `UPDATE` as delete+insert, that FK made every status transition after candidate creation throw `ConstraintException`. Fixed by dropping the FK, matching the existing precedent in migration 0005 (`run_order_events.run_id` has no FK for the identical reason).
- Known overfitting/interpretation limitations: The 30-bar synthetic test fixture is too small to guarantee every candidate produces a non-zero trade (SMA crossovers can occur before the eligibility warm-up ends, yielding zero trades and a `0` objective for some candidates) — this is real, correct engine behavior, not a test bug, and the test suite accounts for it rather than asserting a specific numeric outcome. No walk-forward/rolling-window re-optimization, no multi-objective scoring, no automatic parameter suggestion, and no cross-validation shuffle exist or are planned for v1, per ADR-009. A completed optimization's holdout result is a single sealed evaluation, not a statistically robust out-of-sample estimate — the UI and API consistently label output "research-only," never a prediction or recommendation.

## Next task boundary

TASK-013 performs end-to-end quality, documentation, release-readiness, and operational review. It does not add new research features or relax any integrity safeguard.
