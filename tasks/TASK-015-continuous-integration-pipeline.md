# TASK-015 — Continuous integration pipeline

## Objective

Automate the quality gates every task has run manually since TASK-001: on every push and pull request against `main`, run the full backend and frontend quality gates (and both Docker builds) so a broken change cannot merge unnoticed. This is operational infrastructure only — no product behavior changes.

## Required reading

Read `.claude/CLAUDE.md`, root `README.md` (its "Quality gates" table), `backend/README.md`, `frontend/README.md`, `docs/BUILD_PLAN.md`, and this task.

## Dependencies

TASK-001 through TASK-014 must be complete and verified (all are). This task does not depend on any single prior task's implementation details — it automates the commands already documented for each.

## In scope

- A GitHub Actions workflow (`.github/workflows/ci.yml`) triggered on `push` to `main` and on `pull_request` targeting `main`.
- A backend job: install pinned dependencies (`backend/requirements.txt` + `requirements-dev.txt`), run `ruff format --check .`, `ruff check .`, `mypy .`, `pytest -q`.
- A frontend job: `npm ci`, then `npm run format`, `npm run lint`, `npm run type-check`, `npm run test`, `npm run build`.
- A Docker job: `docker compose build api web` to catch image-build regressions.
- Pinning the same Python/Node versions the rest of the repository already declares (Python 3.13, Node 22).

## Out of scope

- Deployment, hosting, container registry publishing, or release automation.
- Branch-protection rule configuration on GitHub (that is a repository-settings change outside this codebase; documenting the recommendation is in scope, applying it is not, since it requires org/repo admin action outside this task's file-based scope).
- Changing any quality-gate command, dependency version, or tool configuration — this task wires up the *existing* commands, it does not alter them.
- Caching strategy beyond what GitHub Actions' built-in `actions/setup-python`/`actions/setup-node` cache options provide out of the box.

## Test plan

1. Validate the workflow YAML is syntactically correct (`actionlint` if available, otherwise careful manual review) before pushing.
2. Push the branch and confirm the workflow runs and every job (backend, frontend, docker) reports its actual pass/fail state on the resulting pull request — this is the acceptance evidence, since GitHub Actions cannot be simulated locally with full fidelity.
3. Confirm the workflow fails loudly (non-zero exit) if any quality-gate command fails, by reasoning through each step's command (these are the exact commands already verified to pass locally in TASK-013/014).

## Acceptance criteria

- `.github/workflows/ci.yml` runs both services' full quality gates and both Docker builds on every push/PR to `main`.
- The workflow succeeds on this task's own PR, proving it works end-to-end.
- No product code, dependency version, or quality-gate command is changed — only automation is added.

## Definition of done and handoff

After verification, update project memory/index and record:

- Workflow file and jobs added: `.github/workflows/ci.yml` — `backend` (ruff format --check, ruff check, mypy, pytest), `frontend` (prettier, eslint, tsc, vitest, next build), `docker` (`docker compose build api web`). Triggers on `push`/`pull_request` to `main`.
- CI run evidence (link/status): All three jobs passed on PR #31 — backend 1m4s, frontend 1m0s, docker 30s. https://github.com/sugianto43/idx-backtest-lab/actions/runs/30744892375
- Deferred follow-up (e.g. branch protection) and why it's out of scope: Branch-protection rules requiring this workflow before merge were not configured — that's a GitHub repository-settings change (org/repo admin action), not a file in this codebase, so it's outside this task's scope. Recorded as a known limitation in `RELEASE_NOTES.md`.

## Next task boundary

None specific. Future tasks should treat a green CI run on their PR as part of their own verification evidence going forward.
