# IDX Backtesting Lab

Local-first research tooling for transparent, reproducible backtests of Indonesia Stock Exchange (IDX) equities.

> Historical backtests are research artifacts, not investment advice and not a prediction of future performance.

## Current status

TASK-001 through TASK-013 are complete. The system is a working, locally-run
research tool covering the full v1 loop: import market data, define an
instrument and a declarative `sma_crossover` strategy, run and inspect a
single backtest with full audit evidence, and run a bias-safeguarded
parameter optimization with a sealed holdout. See `RELEASE_NOTES.md` for the
exact v1 scope and known limitations, and `.claude/PROJECT_MEMORY.md` for
the full technical history task-by-task.

## What it does

- **Dataset import** — offline, provider-neutral CSV OHLCV ingestion with
  strict validation, immutable versioning, and full provenance (never
  overwrites a prior import).
- **Instruments and corporate actions** — stable opaque instrument IDs,
  effective-dated ticker aliases, and dataset-to-instrument mappings;
  corporate actions are recorded as immutable evidence only (no adjustment
  math).
- **Strategy authoring** — a single, versioned, immutable declarative
  strategy contract in v1: SMA crossover, long-only, next-bar-open fills.
- **Backtest execution** — deterministic execution via a Backtrader adapter
  behind a product-neutral port; every run's manifest, events, portfolio
  snapshots, and 8 documented metrics are persisted as one immutable,
  checksummed artifact bundle with a reproducibility export.
- **Optimization with bias safeguards** — a finite, explicit `fast_window`/
  `slow_window` grid evaluated over chronological train/validation/holdout
  partitions; holdout is sealed until the optimization completes and can
  never influence which candidate is selected; every candidate, rejection,
  and failure is recorded, never silently dropped.
- **Web dashboard** — a strict-TypeScript Next.js frontend consuming one
  typed API client: dataset/run/strategy/optimization workflows, accessible
  loading/empty/warning/unavailable/error states, and a persistent
  research-only disclaimer. The browser never performs a financial
  calculation — every number comes from the backend as a decimal string.

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI + DuckDB application; see `backend/README.md` |
| `frontend/` | Next.js/TypeScript application; see `frontend/README.md` |
| `docs/` | Product, technical, data, API, and decision documentation (including `docs/adr/`) |
| `tasks/` | Executable work specifications, one per implemented task |
| `.claude/` | Persistent operating context for AI-assisted work (`PROJECT_MEMORY.md`, `TASK_INDEX.md`) |

## Prerequisites

- Docker and Docker Compose (recommended path)
- Or locally: Python 3.13 and Node.js 22, for running each service without containers

## Start the local development environment

```bash
docker compose up
```

- API: http://localhost:8000/health (liveness), http://localhost:8000/api/v1/ready (readiness)
- Web: http://localhost:3000

To run each service without Docker — including required environment
variables (`backend/.env.example`, `frontend/.env.example`) — see
`backend/README.md` and `frontend/README.md`.

## Quality gates

| Service | Format | Lint | Type check | Tests | Build |
| --- | --- | --- | --- | --- | --- |
| `backend/` | `ruff format --check .` | `ruff check .` | `mypy` | `pytest -q` | — |
| `frontend/` | `npm run format` | `npm run lint` | `npm run type-check` | `npm run test` | `npm run build` |

Both must pass, along with `docker compose build`, before any change is
considered complete. `.github/workflows/ci.yml` runs all of the above
automatically on every push and pull request against `main`. See
`.claude/CLAUDE.md` for the full working loop and `.claude/TASK_INDEX.md`
for per-task verification evidence.

## AI-assisted development

Read `.claude/CLAUDE.md` before changing the repository. It defines
required read order, research-integrity rules, verification expectations,
and handoff format. `.claude/PROJECT_MEMORY.md` records verified,
task-by-task technical history; `.claude/TASK_INDEX.md` tracks task status
and dependencies.

## License and data

No license has been selected yet. Do not add, redistribute, or commit
market data until provider terms, provenance, and licensing have been
formally decided.
