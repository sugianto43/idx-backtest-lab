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

- Optimization schema/settings/candidate limit:
- Partition, objective, tie-break, and holdout sealing behavior:
- API/routes and audit fields:
- Commands/tests and results:
- Known overfitting/interpretation limitations:

## Next task boundary

TASK-013 performs end-to-end quality, documentation, release-readiness, and operational review. It does not add new research features or relax any integrity safeguard.
