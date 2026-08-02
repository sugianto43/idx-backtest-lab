# TASK-013 — End-to-end quality, documentation, and release readiness

## Objective

Verify the whole system (TASK-001 through TASK-012) is coherent, honest, and consistently documented as a v1 local research tool. Bring root-level documentation up to date with what actually exists, run every quality gate across both services, prove the full user journey works end-to-end through a live Docker environment, and record known v1 limitations explicitly. This task adds no new product behavior and relaxes no integrity safeguard — it is a verification and documentation pass.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/PROJECT_MEMORY.md`, `.claude/TASK_INDEX.md`, `docs/BUILD_PLAN.md`, `docs/PRD.md`, `docs/DATA_GOVERNANCE.md`, root `README.md`, `backend/README.md`, `frontend/README.md`, ADR-001 through ADR-009, and this task.

## Dependencies

TASK-001 through TASK-012 must be complete and verified (all are, per `.claude/TASK_INDEX.md`).

## In scope

- Running and recording the full backend quality gate (`ruff format --check`, `ruff check`, `mypy`, `pytest -q`) and full frontend quality gate (`npm run format`, `npm run lint`, `npm run type-check`, `npm run test`, `npm run build`) from a clean checkout.
- Building both Docker images (`docker compose build`) and proving one complete end-to-end user journey through the live containers: dataset import → instrument → instrument mapping → strategy creation → backtest run creation/execution → run artifacts/metrics retrieval → optimization creation/execution, via real HTTP calls.
- Rewriting the root `README.md` so it accurately describes the current product (not the TASK-001-only bootstrap state): repository layout, all implemented capabilities, setup/run instructions, quality-gate commands, and environment variables required by each service.
- Reviewing `.claude/PROJECT_MEMORY.md` and `.claude/TASK_INDEX.md` for internal consistency with the current codebase (status columns, dependency chains) and correcting anything stale.
- Confirming `backend/.env.example` and `frontend/.env.example` list every environment variable each service actually reads.
- Writing a `RELEASE_NOTES.md` (or equivalent root-level document) that honestly enumerates v1 scope and known limitations: single-instrument long-only `sma_crossover` only, no charting, no authentication, local-only DuckDB persistence, research-only labeling throughout, and any other boundary already documented per-task.
- Confirming no secrets or generated database files are committed (`.gitignore` correctness) and that `git status` on `main` after this task's merge is clean.

## Out of scope

- New product features, new API endpoints, new frontend routes, or any change to financial/execution/optimization semantics.
- New ADRs or relaxing/removing any existing bias, integrity, or safety safeguard from TASK-001 through TASK-012.
- Introducing CI pipeline configuration, deployment infrastructure, or hosting — this task documents and verifies the existing local-first Docker Compose workflow only, it does not add new operational infrastructure.

## Test plan

1. From a clean state, run the full backend quality gate and record exact pass/fail counts.
2. From a clean state, run the full frontend quality gate (including production build) and record exact pass/fail counts.
3. Build both Docker images from scratch and run a single live end-to-end smoke test exercising every major capability (dataset → instrument → mapping → strategy → run → execute → artifacts → optimization → execute) via real HTTP requests against the running containers, plus an SSR/shell check of the equivalent frontend routes.
4. Diff-review root `README.md`, `.claude/PROJECT_MEMORY.md`, and `.claude/TASK_INDEX.md` against the actual codebase for staleness before and after edits.
5. Confirm `.env.example` files list every variable read by `app/infrastructure/settings.py` (backend) and every `NEXT_PUBLIC_*`/build-time variable the frontend reads.

## Acceptance criteria

- All backend and frontend quality gates pass with zero errors, recorded with exact commands and counts.
- Both Docker images build and a single live end-to-end journey succeeds through real HTTP calls, proving the whole stack works together, not just each task in isolation.
- Root `README.md` accurately reflects the current, full state of the product.
- `RELEASE_NOTES.md` (or equivalent) honestly states v1 scope and limitations without overstating capability or implying investment advice.
- `.claude/PROJECT_MEMORY.md` and `.claude/TASK_INDEX.md` are internally consistent with the codebase.
- No secrets, credentials, or generated database artifacts are committed.

## Definition of done and handoff

After verification, update project memory/index and record:

- Backend/frontend quality-gate commands and results:
- End-to-end smoke-test evidence:
- Documentation files updated and why:
- Known v1 limitations recorded:
- Any staleness found and corrected in prior task records:

## Next task boundary

None. This is the final task in the current backlog. Any further work requires a new task definition and, if it changes scope or safeguards, a new ADR.
