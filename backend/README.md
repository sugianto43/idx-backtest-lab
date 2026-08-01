# Backend

FastAPI application for the idx-backtesting-lab API. TASK-001–TASK-003 provide
the process skeleton, layered package boundaries (`api`, `application`,
`domain`, `infrastructure`), health/readiness endpoints, typed configuration,
structured logging with correlation IDs, a safe error envelope, and a local
DuckDB persistence boundary (dataset provenance metadata and immutable
backtest-run manifests only — no market bars or result artifacts yet). See
`.claude/ARCHITECTURE_RULES.md`, `docs/TDD.md`, and
`docs/adr/ADR-002-local-persistence-and-schema-evolution.md`.

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
