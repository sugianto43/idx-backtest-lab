# TASK-006 — Backtest domain model and configuration manifest

## Objective

Implement immutable, validated strategy specifications and backtest run manifests that make every v1 simulation assumption explicit. Create/retrieve/validate these research requests, but do not execute a strategy, place simulated orders, or calculate a result.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/AI_AGENT_CONSTITUTION.md`, `.claude/ARCHITECTURE_RULES.md`, `docs/DATA_GOVERNANCE.md`, `docs/BACKTEST_MANIFEST_CONTRACT.md`, ADR-004, ADR-005, TASK-003 through TASK-005, and this task.

## Dependencies

TASK-002, TASK-003, and TASK-005 must be completed and verified. TASK-004 datasets must be available for end-to-end manifest validation. Reuse immutable persistence, resolved instrument identity, error/correlation, and migration conventions.

## In scope

- Domain values and validation for strategy specification v1 and run manifest v1.
- Immutable persistence/repository ports for strategy versions and fully materialized run manifests.
- API endpoints to create/list/get strategy versions; validate/create/list/get run requests.
- Canonical JSON serialization and deterministic checksums.
- Run status remains `created` after manifest validation; no worker, engine, order, fill, or artifact is created.

## Out of scope

- Backtrader or another execution engine; price/indicator computation; signal generation; simulated trades; portfolio values; metrics.
- Arbitrary strategy code, uploads, scripting, plugins, optimization, short selling, leverage, intrabar execution, or same-bar fill.
- New corporate-action adjustment calculations or silent normalization of data.
- Frontend implementation.

## Persistence model

Add migrations only for:

- `strategy_specs`: `strategy_id`, version, schema version, name, kind, canonical specification JSON, checksum, created timestamp; uniqueness on strategy/version and checksum as appropriate.
- The existing `backtest_runs` envelope from TASK-003: evolve it through a new migration to store schema version, canonical manifest/checksum, exact strategy/dataset references, and state needed for validated `created` runs. Do not rewrite historic rows.

Repositories expose product-neutral methods to create/get/list strategy versions and create/get/list run manifests. Creation must be append-only. Identical requests may return an existing immutable record only under a documented idempotency key/policy; absent such a policy, create a distinct run ID with the same manifest checksum and make the duplication visible.

## API contract

Use standard `/api/v1` envelope/pagination rules. Implement and contract-test:

| Method | Path | Behavior |
| --- | --- | --- |
| `POST` | `/api/v1/strategies` | Create strategy version 1 with validated declarative spec. |
| `GET` | `/api/v1/strategies` | Paginated strategy/version metadata. |
| `GET` | `/api/v1/strategies/{strategy_id}/versions/{version}` | Full immutable specification and checksum. |
| `POST` | `/api/v1/backtest-runs` | Validate/materialize and persist a run manifest with status `created`. |
| `GET` | `/api/v1/backtest-runs` | Paginated immutable run metadata/status. |
| `GET` | `/api/v1/backtest-runs/{run_id}` | Full manifest, checksum, status, warnings (if any), no results. |

Return `422 validation_error` for any undeclared/ambiguous assumption, nonexistent/unsupported reference, invalid timing, unresolved identifier, incompatible dataset policy, or unsupported v1 strategy feature. Return `409 conflict` for immutable version conflicts.

## Implementation rules

- Materialize all v1 defaults into the saved manifest before checksum/persistence.
- Use Decimal/value objects for capital, sizing fractions, fees, and rate-like values even though no calculation occurs.
- Reject JSON numbers for monetary/rate fields if exact decimal-string format is required by the contract.
- Make checksum implementation independent of database ordering and runtime locale/timezone.
- Strategy spec and run manifest validation must be pure/testable domain/application logic, separate from HTTP and database adapters.
- Do not call an engine or inspect bars to compute indicators. Coverage/identity/metadata compatibility checks are allowed.

## Test plan

1. Valid `sma_crossover` strategy v1 persists as a canonical immutable version with deterministic checksum.
2. Invalid windows, unknown kind/fields, unsupported features, and malformed decimal parameters reject safely.
3. Equivalent semantically canonical payloads generate documented identical checksums; materially different assumptions do not.
4. Valid manifest resolves exact dataset/strategy/instrument references and remains `created` with no result artifacts.
5. Missing/unknown data policy, same-bar fill, bad period/interval, unresolved instrument, incompatible adjustment policy, absent execution parameter, invalid decimal/currency, and unknown schema versions reject.
6. Stored manifests contain all defaults and can be fetched/listed without mutation.
7. API errors, pagination, correlation IDs, migrations, repository behavior, lint/format/type checks pass offline.
8. Tests prove no engine invocation, bars/indicator calculations, orders, fills, or metrics occur.

## Acceptance criteria

- Strategy and run manifest contracts follow ADR-005 and the published schema exactly.
- Every persisted run is reproducible from immutable exact references, fully materialized assumptions, canonical JSON, and checksum.
- v1 timing prevents same-bar/implicit execution and v1 restrictions are enforced.
- No simulation or financial result behavior is introduced.
- All required quality checks and offline tests pass; docs/status/handoff contain verified facts only.

## Definition of done and handoff

After all checks pass, update project memory/index and replace these placeholders:

- Schema/migration version:
- Canonical serialization/checksum policy:
- Implemented API contracts:
- Commands/tests and results:
- Explicit deferred execution/financial semantics:

## Next task boundary

TASK-007 executes only a validated run manifest through a Backtrader adapter and produces deterministic engine-neutral raw artifacts. It must not expand the v1 strategy or manifest language without a new ADR/task.
