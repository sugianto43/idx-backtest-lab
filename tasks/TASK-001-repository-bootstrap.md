# TASK-001 — Repository bootstrap and developer tooling

## Objective

Establish a runnable, quality-gated monorepo foundation for the API and web application without implementing market-data or backtesting behavior.

## Context

Read `.claude/CLAUDE.md`, `.claude/MASTER_CONTEXT.md`, `docs/adr/ADR-001-initial-technology-boundaries.md`, and this task before changes.

## Dependencies

None.

## Scope

Allowed areas: root tooling/configuration, `backend/`, `frontend/`, `docs/adr/`, `.claude/PROJECT_MEMORY.md`, and this task/status index.

Forbidden: market-data provider integration, DuckDB schema, strategy semantics, backtesting execution, user authentication, or committing credentials/data.

## Requirements

- Provide Docker-based local API and web development services.
- Configure Python formatting, linting, strict type checking, and tests.
- Configure TypeScript strict checks, formatting, linting, and tests.
- Provide a dependency-free API liveness endpoint and a minimal accessible web landing page.
- Document startup, product boundary, and AI operating instructions.

## Acceptance criteria

- Root documentation explains the repository, local prerequisites, startup path, and quality commands.
- Docker Compose defines API and web development services with isolated dependency volumes and no committed secrets.
- The API serves `GET /health` with `{"status":"ok"}` after dependencies are installed.
- The web service renders an accessible landing page after dependencies are installed.
- Backend and frontend have formatter, linter, type-check, and test commands.
- No data credentials, market data, or unapproved simulation assumptions are present.

## Test plan

- Run Python lint, format check, type check, and unit test.
- Run TypeScript type check, lint, format check, and test command.
- Validate Docker Compose configuration.

## Definition of done

All acceptance criteria and test plan checks pass, task/index/project memory status is current, and no unrelated product capability was introduced.

## Handoff notes

The bootstrap does not make a data source or database schema decision. TASK-002 owns the next API slice; TASK-003 owns DuckDB persistence.

### Backend (`backend/`)

- Python 3.13, FastAPI 0.141.1, Uvicorn 0.52.0 (`requirements.txt`). Dev tools: ruff 0.16.1, mypy 2.3.0, pytest 9.1.1, httpx 0.28.1 (`requirements-dev.txt`).
- `app/main.py` exposes `GET /health` → `200 {"status":"ok"}`. No other routes.
- Commands (run from `backend/` with `.venv` active):
  - `ruff format --check .` → passed, 5 files already formatted.
  - `ruff check .` → passed, all checks passed.
  - `mypy` (strict, configured in `pyproject.toml`) → passed, no issues in 4 source files.
  - `pytest -q` → passed, 1 passed (health endpoint status code + payload).

### Frontend (`frontend/`)

- Next.js 16.2.12 (App Router, Turbopack), React 19.2.4, strict TypeScript (scaffolded via `create-next-app`). Landing page at `app/page.tsx` renders one `<h1>` inside a `<main>` landmark.
- Test stack: Vitest 4 + @testing-library/react 16 + jsdom. Format/lint: Prettier 3 + ESLint 9 (`eslint-config-next` + `eslint-config-prettier`).
- Commands (run from `frontend/`):
  - `npm run format` (prettier --check) → passed after one `format:write` pass.
  - `npm run lint` (eslint) → passed, no findings.
  - `npm run type-check` (tsc --noEmit) → passed, no errors.
  - `npm run test` (vitest run) → passed, 2/2 tests (single heading, main landmark).
  - `npm run build` (next build) → passed, static output generated.
  - `npm run dev` smoke-verified on an alternate port (3100): `GET /` returned `200` with the expected heading.

### Docker

- Root `docker-compose.yml` defines `api` (port 8000, bind-mounts `backend/`) and `web` (port 3000, bind-mounts `frontend/` with `node_modules` in an isolated named volume).
- `docker compose config` → parsed successfully, no errors.
- `docker compose build` → both images (`idx-backtest-lab-api`, `idx-backtest-lab-web`) built successfully.
- Functional smoke test: built images run standalone via `docker run` on alternate host ports (18000/13000) because ports 3000/8000 were already bound by unrelated pre-existing processes on the verification host. `GET http://localhost:18000/health` → `{"status":"ok"}`; `GET http://localhost:13000/` → HTML containing `<h1>IDX Backtesting Lab</h1>`. Both containers were stopped and removed after verification; no state persisted.

### Assumptions/adaptations

- Backend dependencies are pinned as direct dependencies only (not a full transitive lockfile), consistent with the absence of a lockfile-capable tool (no `uv`/`poetry` on the bootstrap host). `requirements.txt`/`requirements-dev.txt` record exact versions actually installed and verified.
- Frontend test runner is Vitest (not Jest), since it integrates cleanly with Next.js's Turbopack/SWC pipeline without extra transform configuration. `test.globals: true` is set in `vitest.config.ts` so Testing Library's automatic `afterEach` cleanup registers correctly.
- `next/font/google` (network font loading) was intentionally not used in the landing page to keep the bootstrap layer network-independent at build time; a system font stack is used instead.

### Risks/follow-up

- `npm audit` reports 3 high-severity transitive advisories (`postcss`, `sharp`) bundled with the pinned `next@16.2.12` release. No non-breaking fix is currently available (`npm audit fix --force` would downgrade to `next@9.3.3`). Not remediated in this task; revisit on the next Next.js upgrade.
- Full `docker compose up` was not verified end-to-end on the bootstrap host because host ports 3000 and 8000 were already occupied by unrelated processes outside this repository. Image builds and standalone container runs were verified instead (see above). Re-verify `docker compose up` on a clean host/CI runner before relying on it as the sole startup path.
