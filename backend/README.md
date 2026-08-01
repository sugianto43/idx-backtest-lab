# Backend

FastAPI application for the idx-backtesting-lab API. TASK-001/TASK-002 provide
the process skeleton, layered package boundaries (`api`, `application`,
`domain`, `infrastructure`), health endpoints, typed configuration, structured
logging with correlation IDs, and a safe error envelope. No market-data,
persistence, or strategy behavior exists yet — see
`.claude/ARCHITECTURE_RULES.md` and `docs/TDD.md`.

## Configuration

Settings are typed and loaded from environment variables (prefix `APP_`), all
optional with safe local defaults — see `.env.example`.

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
