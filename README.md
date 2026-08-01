# IDX Backtesting Lab

Local-first research tooling for transparent, reproducible backtests of Indonesia Stock Exchange (IDX) equities.

> Historical backtests are research artifacts, not investment advice and not a prediction of future performance.

## Current status

TASK-001 (repository bootstrap) is complete: a runnable FastAPI backend skeleton
and a Next.js/TypeScript frontend skeleton exist with quality tooling, Docker
Compose development services, and no market-data, persistence, or strategy
behavior. Application features are introduced by subsequent tasks.

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/` | FastAPI application (`GET /health`) and Python quality tooling; see `backend/README.md` |
| `frontend/` | Next.js/TypeScript application shell; see `frontend/README.md` |
| `docs/` | Product, technical, data, API, and decision documentation |
| `tasks/` | Executable work specifications |
| `.claude/` | Persistent operating context for AI-assisted work |

## Prerequisites

- Docker and Docker Compose (recommended path)
- Or locally: Python 3.13 and Node.js 22, for running each service without containers

## Start the local development environment

```bash
docker compose up
```

- API: http://localhost:8000/health
- Web: http://localhost:3000

To run each service without Docker, see `backend/README.md` and
`frontend/README.md` for setup and quality-check commands.

## Quality gates

| Service | Format | Lint | Type check | Tests |
| --- | --- | --- | --- | --- |
| `backend/` | `ruff format --check .` | `ruff check .` | `mypy` | `pytest -q` |
| `frontend/` | `npm run format` | `npm run lint` | `npm run type-check` | `npm run test` |

## How Claude Code should begin

1. Read `.claude/CLAUDE.md` and its required read order.
2. Read `docs/PRD.md`, `docs/TDD.md`, and the relevant ADRs in `docs/adr/`.
3. Read the target task in `tasks/`.
4. Create only the files permitted by that task, verify its acceptance criteria, then update task status and project memory.

## AI-assisted development

Read `.claude/CLAUDE.md` before changing the repository. It defines required read order, research-integrity rules, verification expectations, and handoff format.

## License and data

No license has been selected yet. Do not add, redistribute, or commit market data until provider terms, provenance, and licensing have been formally decided.
