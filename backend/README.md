# Backend

FastAPI application for the idx-backtesting-lab API. TASK-001 provides only the
process skeleton and quality tooling: a dependency-free `/health` endpoint and
no market-data, persistence, or strategy behavior. `.claude/ARCHITECTURE_RULES.md`
and `docs/TDD.md` govern the layered package layout introduced by later tasks
(`api`, `application`, `domain`, `infrastructure`).

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
