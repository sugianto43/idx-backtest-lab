# Release Notes — v1 (TASK-001 through TASK-016)

This is a local-first research tool for generating auditable evidence about
a single declarative trading strategy against historical Indonesian equity
data. It is not a trading platform, not a data provider, and not a source
of investment advice. Every backtest and optimization result is a
historical simulation only.

## What v1 can do

- Import provider-neutral daily OHLCV CSV data with strict validation,
  immutable versioning per import, and full provenance.
- Define stable instrument identities and effective-dated ticker aliases;
  map a dataset's raw identifiers to an instrument for a declared date
  range.
- Record corporate actions as immutable evidence (no price/share
  adjustment is calculated anywhere in the system).
- Author immutable, versioned `sma_crossover` strategy specifications
  (long-only, next-bar-open fills, bar-close signal timing).
- Create and execute a single-instrument backtest run, and retrieve its
  full immutable artifact bundle: order/fill/position/cash events,
  per-bar portfolio snapshots, 8 documented metrics (each explicitly
  `available` or `not_available` with a reason — never fabricated or
  zero-substituted), and a reproducibility manifest export.
- Run a finite-grid parameter optimization over `fast_window`/`slow_window`
  with chronological train/validation/holdout partitions. Holdout is
  sealed from candidate selection and evaluated exactly once for the
  selected candidate; every candidate, rejection, and failure is
  persisted and visible.
- Browse all of the above through an accessible, strict-TypeScript web
  dashboard that performs no financial calculation itself — every number
  displayed comes directly from the backend as a decimal string. Datasets,
  strategies, backtest runs, and optimizations can all be created and
  executed entirely from the browser.

## Known v1 limitations

- **Single instrument only.** Multi-instrument backtest runs and
  optimizations are explicitly rejected.
- **One strategy kind.** Only `sma_crossover` exists — long-only, no short
  selling, no custom code or expressions, no other indicator.
- **No charting.** All evidence is presented as structured data and
  tables; no client-side or server-side chart rendering exists.
- **8 fixed metrics.** `initial_equity`, `final_equity`, `total_return`,
  `annualized_return`, `max_drawdown`, `trade_count`, `win_rate`,
  `realized_pnl`, `exposure_time_ratio` — no Sharpe/Sortino/custom
  objective, and optimization objectives are restricted to this same set.
- **Optimization search is finite-grid only.** No random, Bayesian, or
  genetic search; no walk-forward rolling re-optimization; no
  cross-validation shuffle; no multi-objective scoring. Objective ranking
  is always "highest value wins" — there is no minimize direction, because
  every v1 metric is already oriented so a higher value is better.
- **One market-data provider: Yahoo Finance, personal use only.**
  `POST /api/v1/datasets:import-from-yahoo-finance` (ADR-010) fetches daily
  OHLCV via Yahoo's public, unofficial chart endpoint. Yahoo's Terms of
  Service permit personal, non-commercial use only and prohibit
  redistribution — this tool must never be deployed as a hosted,
  multi-tenant, or commercial service on top of this adapter without a
  real licensing review. Manual CSV import remains fully supported for any
  other source.
- **No authentication or multi-user support.** Anyone with network access
  to the API can perform every operation. This is a local single-user
  research tool, not a hosted service.
- **Local persistence only.** DuckDB is a single local file; there is no
  distributed execution, no concurrent-run scaling, and no managed backup.
- **No hosted deployment.** `.github/workflows/ci.yml` (TASK-015)
  automates every quality gate and both Docker builds on push/PR to
  `main`, but no production hosting, container registry publishing, or
  release automation exists in this repository. Branch-protection rules
  requiring the CI workflow to pass before merge have not been configured
  (a repository-settings change outside this codebase's scope).

## Verification evidence (TASK-013)

- Backend: `ruff format --check .`, `ruff check .`, `mypy .`, `pytest -q`
  — all clean, 280 tests passed.
- Frontend: `npm run format`, `npm run lint`, `npm run type-check`,
  `npm run test`, `npm run build` — all clean, 84 tests passed, 13 routes
  built.
- `docker compose build api web` — both images build successfully.
- Live end-to-end smoke test against the built Docker images: dataset
  import → instrument → instrument mapping → strategy creation → backtest
  run creation/execution → run summary/artifacts/reproducibility-manifest
  retrieval → optimization creation/execution (reached `completed`) — all
  succeeded via real HTTP calls. All 9 frontend routes (`/`, `/datasets`,
  `/datasets/import`, `/runs`, `/strategies`, `/strategies/new`,
  `/optimizations`, `/optimizations/new`, `/system`) returned `200` from
  the live web container pointed at the live API container.

## Verification evidence (TASK-014)

- Frontend: `npm run format`, `npm run lint`, `npm run type-check`,
  `npm run test`, `npm run build` — all clean, 90 tests passed, 14 routes
  built (adds `/runs/new` and an execute action on `/runs/{run_id}`).
- `docker compose build web` succeeds; a live smoke test against the built
  images confirmed `/runs/new`'s SSR shell renders, and a run created via
  the exact payload the form sends reached `completed` after calling the
  same execute endpoint the detail page's new "Execute run" button uses.

## Verification evidence (TASK-015)

- `.github/workflows/ci.yml` ran on its own pull request (#31) and all
  three jobs passed: Backend quality gate (1m4s), Frontend quality gate
  (1m0s), Docker image builds (30s) —
  https://github.com/sugianto43/idx-backtest-lab/actions/runs/30744892375.

## Verification evidence (TASK-016)

- Backend: `ruff format --check .`, `ruff check .`, `mypy .`, `pytest -q`
  — all clean, 289 tests passed (9 new: CSV-conversion unit tests with a
  mocked fetch function, plus API tests for success/fetch-failure/
  duplicate-conflict, all offline).
- `docker compose build api` succeeds; a live smoke test against the
  running container made a real network call to Yahoo Finance for `AAPL`
  and correctly imported 6 real trading bars with fixed provenance
  (`source_name="Yahoo Finance"`, the personal/non-commercial license
  citation, `adjustment_policy="split_adjusted"`) — not a mocked response.
