# Backend

FastAPI application for the idx-backtesting-lab API. TASK-001–TASK-006 provide
the process skeleton, layered package boundaries (`api`, `application`,
`domain`, `infrastructure`), health/readiness endpoints, typed configuration,
structured logging with correlation IDs, a safe error envelope, a local
DuckDB persistence boundary, offline provider-neutral CSV market-data
ingestion, instrument/corporate-action identity records, and immutable
strategy/run-manifest validation. See `.claude/ARCHITECTURE_RULES.md`,
`docs/TDD.md`, `docs/adr/ADR-002-local-persistence-and-schema-evolution.md`,
ADR-003, ADR-004, ADR-005, `docs/CSV_INGESTION_CONTRACT.md`,
`docs/INSTRUMENT_AND_CORPORATE_ACTION_CONTRACT.md`, and
`docs/BACKTEST_MANIFEST_CONTRACT.md`.

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
defines exactly one supported value for each in v1.

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
No market-data provider, corporate-action, or ticker-resolution logic exists
here; see TASK-005.

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
