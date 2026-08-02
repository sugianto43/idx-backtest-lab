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
  - `backend/migrations/0004_add_strategy_specs_and_run_manifests.sql` (version 4): new `strategy_specs` table (PK `(strategy_id, version)`, `kind` CHECK `'sma_crossover'` only); `backtest_runs` gains nullable `schema_version`, `manifest_checksum`, `strategy_id`, `strategy_version` columns (DuckDB `ALTER TABLE ADD COLUMN` still cannot add `NOT NULL`/`CHECK`, same limitation documented in TASK-004 — enforced in `RunManifest.__post_init__` instead). No historic `backtest_runs` rows existed to rewrite (TASK-003 never shipped a create-run endpoint), so this is purely additive.
- Canonical serialization/checksum policy:
  - `app/domain/checksum.py`: `canonical_json_bytes()` = `json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")`; `compute_checksum()` = `"sha256:" + sha256(canonical_json_bytes(data)).hexdigest()`. Every domain value object (strategy parameters/signal-policy, and every run-manifest nested object) has a `to_canonical_dict()` producing exactly the contract's JSON shape. Decimal fields are serialized via `format(value, "f")` (never `float`), preserving the exact input precision (e.g. `"100000000.00"` stays `"100000000.00"`). Verified by test: semantically-equivalent payloads (same content, different construction order) produce identical checksums; materially different values produce different checksums.
- Implemented API contracts:
  - `POST /api/v1/strategies`, `GET /api/v1/strategies`, `GET /api/v1/strategies/{strategy_id}/versions/{version}`.
  - `POST /api/v1/backtest-runs`, `GET /api/v1/backtest-runs`, `GET /api/v1/backtest-runs/{run_id}`.
  - All under `/api/v1`, standard error envelope. `404 not_found` for unknown strategy/dataset/instrument references. `422 validation_error` for domain validation failures (invalid parameters, unsupported v1 feature value, period outside dataset coverage, non-decimal monetary/rate string), with `details[0].code` carrying the specific stable validation code (e.g. `unsupported_feature`, `period_out_of_coverage`, `invalid_parameters`).
- Commands/tests and results (from `backend/` with `.venv` active):
  - `ruff format --check .` → passed, 99 files already formatted.
  - `ruff check .` → passed, all checks passed.
  - `mypy` (strict) → passed, no issues in 98 source files.
  - `pytest -q` → passed, 203 passed: checksum determinism/sorting, strategy-spec domain validation (window ordering, price field, signal policy, schema version), run-manifest domain validation (every fixed-`kind` field rejection, period ordering, capital/fraction/rounding bounds, universe dedup, checksum determinism, exact-decimal-string preservation), `strategy_specs` repository round-trip/pagination, application-service orchestration with in-memory fakes (not-found for strategy/dataset/instrument, period-out-of-coverage, invalid decimal string, successful persistence), and full API contract tests for both `/strategies` and `/backtest-runs` (using a real CSV-imported dataset + created instrument, via a real temporary DuckDB per test).
  - `docker compose build api` → image built successfully (no new dependencies). Standalone `docker run` smoke test: real `curl` `POST`/`GET /api/v1/strategies` against the running container returned a strategy with a `sha256:...` checksum, matching on repeat fetch.
- Explicit deferred execution/financial semantics:
  - No engine invocation, no bars/indicators read, no orders/fills/portfolio values, no metrics computed — `backtest_runs.status` stays `created` for every run this task produces; `engine_version`/`engine_ref.adapter_version` is the literal string `"unimplemented"`. All of that is TASK-007/TASK-008 scope.
  - **Deliberate v1 scope reduction (see also `PROJECT_MEMORY.md`):** commission/tax/slippage/liquidity/price-limit/benchmark/signal-and-fill/corporate-action-treatment are NOT exposed as caller-configurable request fields — they are fixed constants in `app/domain/backtest_manifest.py`, materialized into every persisted manifest exactly as the contract's fixed v1 values, because the contract defines only one legal value for each in v1. This was chosen over adding request fields that could only ever validate to one value, per "smallest coherent change." If a future task needs these genuinely configurable, add new request fields and validate against an expanded allowed set — do not silently loosen the existing constants.
  - `period.bar_interval` is always derived from the referenced dataset's own declared `bar_interval`, not accepted as a separate request field — makes the contract's "dataset interval must equal requested interval" rule true by construction.
  - `dataset_ref.content_checksum` uses the dataset's own `content_checksum` (may be an empty string if a future ingestion path leaves it unset — TASK-004's CSV path always sets it from the uploaded file's SHA-256, so this is currently always populated in practice).

## Next task boundary

TASK-007 executes only a validated run manifest through a Backtrader adapter and produces deterministic engine-neutral raw artifacts. It must not expand the v1 strategy or manifest language without a new ADR/task.
