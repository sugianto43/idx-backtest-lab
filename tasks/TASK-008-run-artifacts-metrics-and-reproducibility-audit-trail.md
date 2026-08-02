# TASK-008 — Run artifacts, metrics, and reproducibility audit trail

## Objective

Persist immutable, auditable artifacts from TASK-007 execution results; derive the v1 documented portfolio snapshots and metrics; and expose safe retrieval/export APIs. A visible result must be traceable to exact input/version/checksum evidence.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/AI_AGENT_CONSTITUTION.md`, `.claude/ARCHITECTURE_RULES.md`, `.claude/TEST_GUIDE.md`, `docs/BACKTEST_MANIFEST_CONTRACT.md`, `docs/ENGINE_EXECUTION_CONTRACT.md`, `docs/RESULT_ARTIFACT_AND_METRIC_CONTRACT.md`, ADR-005 through ADR-007, TASK-006, TASK-007, and this task.

## Dependencies

TASK-006 and TASK-007 must be completed and verified. Use their canonical manifests, deterministic `ExecutionResult`, lifecycle, engine metadata, and explicit v1 execution limitations. Do not change their timing or calculation semantics.

## In scope

- Append-only artifact persistence/migrations/repositories for execution events, portfolio snapshots, metric records, artifact bundle metadata, and reproducibility manifests.
- Pure deterministic projection/calculation from `ExecutionResult` plus exact run manifest/dataset snapshot.
- FIFO lot matching limited to the documented v1 trade-count/win-rate/realized-P&L definition.
- Safe API retrieval of run summary, artifact details, events, snapshots, metrics, and reproducibility-manifest export.
- Compatibility assessment for run comparison metadata; numerical comparison UI is deferred.

## Out of scope

- Altering engine order/fill/rounding/timing, adding execution assumptions, or mutating any source/run manifest.
- New metrics, Sharpe/volatility/benchmark performance, currency conversion, corporate-action transformation, forward-filled valuation, tax modeling beyond recorded events, or optimization.
- Frontend/dashboard work, charts, CSV/PDF reports, background jobs, retention/deletion policy, external analytics.

## Persistence design

Create an ordered migration with append-only tables (exact names may follow established conventions):

- `run_artifact_bundles`: bundle ID, run ID unique, schema version, checksum, terminal status, provenance JSON, event/snapshot/metric counts, creation timestamp.
- `run_order_events`, `run_fill_events`, `run_position_events`, `run_cash_events`, `run_warnings`: event identity/order, bundle/run ID, product-neutral fields, payload/checksum as needed.
- `portfolio_snapshots`: bundle/run ID, sequence/timestamp, cash, holdings value, total equity, currency, valuation status/reason.
- `run_metrics`: bundle/run ID, metric key, decimal/null value, availability status/reason, definition version, calculation-input JSON.
- `reproducibility_manifests`: bundle/run ID, canonical export JSON, checksum, created timestamp.

Require a unique artifact bundle per run, immutable inserts, chronological/sequence constraints, safe JSON handling, and foreign references to the exact run. Store monetary values as decimal-safe text/structured values, never float. Do not persist Backtrader objects or arbitrary pickles.

Artifact creation must be transactional as far as the storage supports: either a complete consistent terminal bundle exists, or it is marked/recorded safely as failed with no misleading partial metrics. Rerunning requires a new run ID, never replacement.

## Calculation requirements

- Project portfolios only from ordered TASK-007 events and declared dataset close prices according to the valuation policy.
- Keep calculation code framework/database/engine independent and testable with small hand-calculated fixtures.
- Apply deterministic FIFO lots per instrument for completed-trade metrics. Define entry/exit matching explicitly in code/docs and persist input components needed to audit a value.
- Include recorded commission/tax/slippage components in realized P&L when nonzero. V1 normally has zero components but must not assume this silently.
- Use manifest `annualization_basis` and session count exactly as documented. Do not substitute calendar days.
- Return `not_available` status/reason for insufficient/invalid valuation inputs; do not throw away warning evidence or coerce to zero.
- Compute/check bundle and reproducibility-manifest checksums using documented canonical serialization.

## API contract

Use standard error/correlation/pagination behavior. Add and contract-test:

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/v1/backtest-runs/{run_id}/summary` | Status, provenance summary, metric statuses/values, warning count; no huge event payload. |
| `GET` | `/api/v1/backtest-runs/{run_id}/artifacts` | Bundle metadata and paginated links/sections. |
| `GET` | `/api/v1/backtest-runs/{run_id}/events` | Paginated, stable-order execution event stream with type filter. |
| `GET` | `/api/v1/backtest-runs/{run_id}/portfolio-snapshots` | Paginated chronological valuation snapshots. |
| `GET` | `/api/v1/backtest-runs/{run_id}/metrics` | Metric records including definition/status/reason. |
| `GET` | `/api/v1/backtest-runs/{run_id}/reproducibility-manifest` | Safe JSON export of documented provenance/checksums only. |
| `GET` | `/api/v1/backtest-runs/{run_id}/comparison-compatibility?other_run_id=...` | Boolean compatibility plus specific reasons; no ranking. |

Return `404 not_found` for unknown runs and a clear stable status/error for runs without a terminal artifact. Never expose source files, database paths, internal exception details, or credentials.

## Test plan

Use tiny synthetic fixtures with manually derivable expected outputs. Test:

1. A completed `ExecutionResult` creates exactly one immutable consistent artifact bundle with correct checksums/provenance.
2. Event ordering, quantities, prices, zero/nonzero cost components, warnings, and terminal status survive persistence/retrieval exactly.
3. Portfolio snapshots value valid closes without forward fill; unvalued holdings generate warnings and unavailable metrics.
4. Each v1 metric matches hand calculation, including drawdown, annualization session basis, FIFO trade matching, costs, zero-trade handling, and decimal rounding.
5. Missing/invalid endpoints, insufficient sessions, invalid valuations, and no trades return `not_available` with reasons rather than zero/guesses.
6. Failed runs do not expose fabricated completed bundles/metrics.
7. Reproducibility manifest contains all required versions/checksums, is canonical/checksummed, and excludes secrets/paths/raw input.
8. Compatibility endpoint accepts only matching declared policies and reports each incompatibility reason.
9. Pagination, API errors, correlation IDs, migrations, immutability, static checks, and full offline suite pass.

## Acceptance criteria

- Artifact and metric behavior follows ADR-007 and the published contract exactly.
- Every persisted numeric result is traceable to events, snapshots, inputs, definitions, and checksum/version evidence.
- Unavailable/ambiguous valuation and metric conditions are visible, never silently filled or rendered as zero.
- Artifacts are append-only/immutable, safely retrievable, and no engine/framework types leak through APIs.
- Comparison compatibility protects against misleading cross-run ranking.
- All tests and quality gates pass; project memory/index/handoff contain verified facts only.

## Definition of done and handoff

After all checks pass, update status documents and complete:

- Migration/artifact schema version: Migration `0005_add_run_artifacts_and_metrics.sql`; `ARTIFACT_SCHEMA_VERSION = 1`, `METRIC_DEFINITION_VERSION = 1` (`app/domain/run_artifact.py`). Tables: `run_artifact_bundles`, `run_order_events`, `run_fill_events`, `run_position_events`, `run_cash_events`, `run_warnings`, `portfolio_snapshots`, `run_metrics`, `reproducibility_manifests`. One bundle row per terminal run (`UNIQUE run_id`); a `FAILED` run's bundle has zero snapshot/metric rows.
- Metric definition implementation notes: 8 metrics computed in `app/domain/run_artifact.py::compute_metrics` — `initial_equity`, `final_equity`, `total_return`, `annualized_return`, `max_drawdown`, `trade_count`, `win_rate`, `realized_pnl`, `exposure_time_ratio`. Each is `available` (with `Decimal` value + `calculation_input_json`) or `not_available` (with a reason string) — never a fabricated/zero-substituted value. `annualized_return` and `total_return` are `not_available` when `initial_equity <= 0`; `annualized_return` is additionally `not_available` when there is only one valid snapshot (`elapsed_sessions == 0`). `win_rate`/`realized_pnl` are based on FIFO-matched SELL fills only.
- Valuation/FIFO edge-case policy: `build_portfolio_snapshots` values cash + holdings at each declared bar's close only (v1 policy, no forward-fill); every v1 snapshot is `status=valid` (no `not_available` snapshot path is exercised yet — reserved for a future non-contiguous-bar scenario). `compute_fifo_realized_pnl` is long-only, single-instrument: BUY fills push `[quantity, price]` lots; a SELL fill matches oldest lots first, and each SELL fill produces exactly one realized-P&L entry (one "trade"), net of that fill's own commission/tax/slippage.
- API endpoints and pagination: `GET /api/v1/backtest-runs/{run_id}/{summary,artifacts,metrics,reproducibility-manifest,comparison-compatibility}` and paginated `GET .../events?type={order|fill|position|cash|warning}&limit&offset` and `GET .../portfolio-snapshots?limit&offset` (default `limit=20`, max `100`). `comparison-compatibility` takes `other_run_id` as a query param and returns `{compatible: bool, reasons: [str, ...]}` — compares manifest schema version, capital currency, bar interval, annualization basis, dataset adjustment policy, and artifact schema version between the two runs; never a numeric ranking.
- Commands/tests and results: `ruff format .`, `ruff check .`, `mypy .` all clean; `pytest -q` → 243 passed (adds `tests/test_run_artifact_domain.py`, `tests/test_run_artifact_writer_and_repository.py`, `tests/test_run_artifacts_api.py`). `docker compose build api` succeeds; a standalone `docker run` end-to-end HTTP smoke test (import dataset → instrument → mapping → strategy → run → execute → fetch all 7 new endpoints) passed, including a self-comparison `comparison-compatibility` check returning `compatible: true`.
- Known limitations/deferred metrics: Portfolio valuation has no `not_available` path exercised in v1 (always `valid`, since bars are always contiguous by contract). No multi-instrument or short-position P&L (matches TASK-006/007's long-only single-instrument v1 scope). `run_metrics.value`/`portfolio_snapshots.*` decimal columns are stored as `VARCHAR`/`DECIMAL(18,6)` respectively — `run_metrics.value` uses `VARCHAR` specifically to preserve exact `Decimal` string round-tripping for ratios (e.g. `annualized_return`) that can exceed `DECIMAL(18,6)` precision. Found and fixed a real ordering bug during implementation: persisting the artifact bundle *before* the run's terminal status transition caused a DuckDB `ConstraintException` (DuckDB implements `UPDATE` as delete+insert, which transiently violates an FK from a child table); the fix is to persist the artifact only after `transition_status` commits — see `execute_backtest_run_service.py`.

## Next task boundary

TASK-009 creates the frontend shell and typed API client. TASK-010 consumes these retrieval endpoints in a dataset/run workflow dashboard. Neither task may recompute financial values in the browser.
