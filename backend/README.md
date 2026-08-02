# Backend

FastAPI application for the idx-backtesting-lab API. TASK-001–TASK-012
provide the process skeleton, layered package boundaries (`api`,
`application`, `domain`, `infrastructure`), health/readiness endpoints,
typed configuration, structured logging with correlation IDs, a safe error
envelope, a local DuckDB persistence boundary, offline provider-neutral CSV
market-data ingestion, instrument/corporate-action identity records,
immutable strategy/run-manifest validation, a deterministic Backtrader
execution adapter, an immutable run-artifact/metrics/reproducibility audit
trail, and an auditable finite-grid parameter optimizer with chronological
train/validation/holdout bias safeguards. See
`.claude/ARCHITECTURE_RULES.md`, `docs/TDD.md`,
`docs/adr/ADR-002-local-persistence-and-schema-evolution.md`, ADR-003,
ADR-004, ADR-005, ADR-006, ADR-007, ADR-009, `docs/CSV_INGESTION_CONTRACT.md`,
`docs/INSTRUMENT_AND_CORPORATE_ACTION_CONTRACT.md`,
`docs/BACKTEST_MANIFEST_CONTRACT.md`, `docs/ENGINE_EXECUTION_CONTRACT.md`,
`docs/RESULT_ARTIFACT_AND_METRIC_CONTRACT.md`, and
`docs/OPTIMIZATION_AND_BIAS_SAFEGUARD_CONTRACT.md`.

## Engine execution

`POST /api/v1/backtest-runs/{run_id}:execute` runs a validated, `created`
manifest through a Backtrader adapter (`app/infrastructure/engine/`) once:
`sma_crossover` signals are computed from declared `close` values at bar
close, and orders fill at the *next* bar's open — never the signal bar's own
close (proven by `tests/test_backtrader_adapter.py`'s smoke fixture). If no
next bar exists for an eligible signal, the whole run fails closed
(`missing_next_bar`). The engine emits an in-memory, product-neutral
`ExecutionResult` (orders/fills/positions/cash/warnings) — Backtrader types
never cross the adapter boundary. The execute endpoint itself still returns
only event counts and a terminal status as an interim summary, but on the
same call the run's full result is now persisted as an immutable artifact
bundle (see below). v1 supports exactly one instrument per run;
multi-instrument manifests are rejected.

## Run artifacts, metrics, and reproducibility

Every terminal run (`completed` or `failed`) gets exactly one immutable
`run_artifact_bundle`, written by `DuckDBRunArtifactWriter`
(`app/infrastructure/db/run_artifact_writer.py`) in a single transaction
right after the run's status transition commits. A `failed` run's bundle
persists its events/warnings only — no portfolio snapshots or metrics are
ever fabricated for a failed run. Retrieval is read-only:

- `GET /api/v1/backtest-runs/{run_id}/summary` — status, terminal status, and
  all metrics in one call.
- `GET /api/v1/backtest-runs/{run_id}/artifacts` — bundle metadata,
  checksum, provenance (manifest/dataset/strategy/engine checksums), and
  links to the sections below.
- `GET /api/v1/backtest-runs/{run_id}/events?type={order|fill|position|cash|warning}&limit&offset`
  — paginated event log, one type per call.
- `GET /api/v1/backtest-runs/{run_id}/portfolio-snapshots?limit&offset` —
  per-bar cash/holdings/equity valuation (v1: bar-close valuation only, no
  forward-fill).
- `GET /api/v1/backtest-runs/{run_id}/metrics` — all 8 v1 metrics
  (`initial_equity`, `final_equity`, `total_return`, `annualized_return`,
  `max_drawdown`, `trade_count`, `win_rate`, `realized_pnl`,
  `exposure_time_ratio`), each `available` (with a `Decimal` value) or
  `not_available` (with a reason) — never a fabricated/zero-substituted
  value.
- `GET /api/v1/backtest-runs/{run_id}/reproducibility-manifest` — the full
  canonical run manifest plus provenance and checksums, exported as JSON.
- `GET /api/v1/backtest-runs/{run_id}/comparison-compatibility?other_run_id=...`
  — `{compatible, reasons}` only; never a numeric cross-run ranking.

## Optimization

An optimizer (`app/domain/optimization.py`, `app/application/{optimization_manifest_service,execute_optimization_service}.py`,
migration `0006_add_optimizations.sql`) searches only `sma_crossover.fast_window`/`slow_window`
over an explicit finite integer grid, using chronological
`train`/`validation`/`holdout` partitions (`train_end < validation_start <=
validation_end < holdout_start <= holdout_end`, DB-checked and
bar-coverage-checked at creation time). `POST /api/v1/optimizations`
canonicalizes the grid `(fast_window, slow_window)` in stable lexicographic
order, records invalid pairs (`fast_window >= slow_window`) as `rejected`
candidates rather than silently dropping them, and rejects an oversized grid
(`APP_OPTIMIZATION_MAX_CANDIDATE_COUNT`, default 50) before any candidate
runs. `POST /api/v1/optimizations/{id}:execute` runs each pending candidate
through a real train-period run and a real validation-period run (reusing
TASK-006/007/008's existing manifest/execution/artifact paths — one new
immutable strategy version per candidate), ranks only candidates with an
`available` validation objective (never an `unavailable` one), tie-breaks
deterministically (highest objective value, then lower `slow_window`, then
lower `fast_window`, then candidate ID), and evaluates the selected
candidate on holdout exactly once. `GET /api/v1/optimizations/{id}` seals
holdout fields (`null`, `sealed: true`) until the optimization reaches
`completed` — holdout can never influence selection, and reading it early is
impossible even by the API, not just hidden by the UI.
`GET /api/v1/optimizations/{id}/candidates` never includes holdout data. A
candidate's train or validation run failing (e.g. `missing_next_bar`) does
not abort the other candidates — it is recorded as a `failed` candidate with
a reason, and the optimization proceeds. Lifecycle:
`created → validating → running_train_validation → selecting →
running_holdout → completed`, with `failed`/`cancelled` as terminal
alternatives; only documented forward transitions are legal, and a second
`:execute` call on a non-`created` optimization returns `409 conflict`.

## Strategies and backtest runs

`POST /api/v1/strategies` creates an immutable `sma_crossover` v1 strategy
specification (checksummed canonical JSON). `POST /api/v1/backtest-runs`
validates and persists a fully materialized, checksummed run manifest
(exact strategy/dataset references, resolved instrument universe, period
inside the dataset's declared coverage, capital, execution assumptions,
metric settings) with status `created` — **no engine is invoked and no
result is produced here** (TASK-007). Most v1 execution-assumption fields
(commission/tax/slippage `none`, liquidity/price-limit `ignore_with_warning`,
signal/fill timing, benchmark `none`) are fixed constants materialized into
every manifest rather than caller-configurable inputs, since the contract
defines exactly one supported value for each in v1. `GET /api/v1/backtest-runs`
and `GET /api/v1/backtest-runs/{run_id}` also expose `final_equity` and
`total_return` (each `{status, value, reason}`, matching TASK-008's metric
status contract) so the frontend dashboard can list run outcomes without an
extra per-row call — `reason` is `run_not_yet_executed` before the run has
an artifact bundle, or `metric_not_computed` if a bundle exists without that
metric.

## Instruments and corporate actions

Instruments have a stable opaque `instrument_id`; tickers are effective-dated
aliases (`POST /api/v1/instruments/{id}/aliases`), never primary keys. A
dataset's raw `source_instrument_identifier` (from TASK-004) resolves to an
instrument only for a declared date range via
`POST /api/v1/datasets/{dataset_id}/instrument-mappings`. Corporate actions
(`POST /api/v1/instruments/{id}/corporate-actions`) are immutable evidence
records only — no price/share adjustment is calculated anywhere in this
codebase. Overlapping aliases/mappings for the same symbol or source
identifier are rejected with `409 conflict`.

## Dataset import

`POST /api/v1/datasets:import` (multipart: `file` + required metadata fields
`name`, `source_name`, `license_reference`, `bar_interval`, `timezone`,
`adjustment_policy`, `instrument_mapping_policy`; optional `source_reference`,
`allow_reimport`) validates a CSV file against
`docs/CSV_INGESTION_CONTRACT.md` exactly and fails the whole import on any
violation. `GET /api/v1/datasets/{dataset_id}` and `GET /api/v1/datasets`
expose provenance, validation status, and warnings — never raw bars or files.
Both also expose `row_count`/`warning_count` (sourced from the dataset's
latest import record) so the frontend dashboard can render them without a
detail call per row. No market-data provider, corporate-action, or
ticker-resolution logic exists here; see TASK-005.

## Configuration

Settings are typed and loaded from environment variables (prefix `APP_`), all
optional with safe local defaults — see `.env.example`.

## Database

The app uses one local DuckDB file (`APP_DATABASE_PATH`, default
`./data/idx_backtesting_lab.duckdb`, git-ignored). Ordered SQL migrations live
in `migrations/` and are applied once at process startup; `GET /api/v1/ready`
reports `database: "ready"` once they've all been applied, or a `503
dependency_unavailable` envelope otherwise. Migrations are append-only —
never edit an already-released migration file; add a new one instead.

## Prerequisites

- Python 3.13
- pip

## Local setup

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Run the API

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

`GET http://localhost:8000/health` returns `{"status":"ok"}`.

## Quality commands

Run from `backend/` with the virtualenv active:

```bash
ruff format --check .   # formatting
ruff check .             # linting
mypy                      # strict type checking
pytest -q                 # tests
```

Auto-fix formatting with `ruff format .`.

## Docker

From the repository root: `docker compose up api`. The container installs
dependencies from `requirements-dev.txt` and serves the API on port 8000.
