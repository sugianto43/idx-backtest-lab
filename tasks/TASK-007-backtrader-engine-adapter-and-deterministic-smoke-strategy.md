# TASK-007 — Backtrader engine adapter and deterministic smoke strategy

## Objective

Execute a validated Run Manifest v1 through a Backtrader infrastructure adapter and return deterministic, product-neutral raw execution events. Prove that signal timing prevents look-ahead bias with a tiny `sma_crossover` smoke strategy.

## Required reading

Read `.claude/CLAUDE.md`, `.claude/AI_AGENT_CONSTITUTION.md`, `.claude/ARCHITECTURE_RULES.md`, `.claude/TEST_GUIDE.md`, `docs/BACKTEST_MANIFEST_CONTRACT.md`, `docs/ENGINE_EXECUTION_CONTRACT.md`, ADR-005, ADR-006, TASK-004 through TASK-006, and this task.

## Dependencies

TASK-004 and TASK-006 must be completed and verified. Dataset snapshots, resolved instrument identity, valid strategy/run manifests, typed settings, and repository ports must exist. TASK-008 is not a dependency: no durable artifacts or metrics are created here.

## In scope

- An application-owned engine-execution port and an infrastructure Backtrader implementation.
- Translation of exact Run Manifest v1 and normalized bar snapshots to Backtrader inputs, then translation of engine behavior to `ExecutionResult` contract events.
- A use case that transitions an eligible run from `created` to `running` to terminal state while holding raw results in process/temporary test context only.
- Deterministic execution policy, explicit broker setup, safe error mapping/logging, and fixture-driven tests.
- A minimal internal API/command trigger only if needed to exercise the use case; it must not claim result-artifact availability and must not become the final run UX.

## Out of scope

- Persisting result artifacts, equity curves, orders/fills, positions, logs, charts, exports, comparisons, or performance metrics.
- Any new strategy kind, custom code, optimizer, intrabar/same-bar fills, short selling, leverage, partial fills, realistic liquidity, price-limit modeling, costs/taxes/slippage beyond declared `none`.
- Changing dataset bars or applying corporate-action transformations.
- Frontend workflow or background/distributed execution.

## Architecture requirements

- Define the execution port in application code using only product-neutral manifest/snapshot/result types.
- Place all imports of Backtrader and conversion logic in infrastructure. No API/domain/application module may import Backtrader.
- Do not pass a database connection, HTTP request, or persistence model to the adapter.
- Snapshot bars before engine invocation using immutable/ordered values; the adapter may not query repositories or external services.
- Use injected clock/ID generation where result observability would otherwise be nondeterministic.
- Configure Backtrader broker/cerebro settings explicitly; document every setting that affects orders, cash, fill price, commission, and order status.
- Convert engine exceptions/statuses to safe product errors/events; never return a Backtrader object or stack trace.

## Run lifecycle

The application service validates run eligibility, obtains the exact snapshot, then atomically transitions `created → running`. On adapter success it transitions to `completed`; on a handled/engine failure it transitions to `failed` with a stable safe code. Reject duplicate/concurrent execution attempts through expected-status transitions. Because artifacts are not persisted in this task, completed runs must expose a clear interim state/notice that durable result retrieval is introduced in TASK-008.

If this interim lifecycle conflicts with the task-003 status schema, add a forward-compatible migration and document the exact policy; do not fake artifact availability.

## Smoke fixture

Create a minimal synthetic one-instrument daily dataset that makes a crossover and next-bar fill auditable by hand. The fixture must demonstrate:

- No signal before the slow window is available.
- A close-based crossover at bar `t` creates an intent only after that bar closes.
- Fill is at the next bar’s open, not close of `t`.
- A later downward crossover exits only an existing position at the subsequent bar open.
- The same canonical manifest/snapshot produces identical semantic events on repeated execution.

Document the fixture’s expected signal/order/fill timeline in the test, not only in a snapshot file.

## Test plan

1. Adapter imports/executes only through infrastructure and conforms to the product-neutral port/output contract.
2. Smoke fixture proves no look-ahead: signal timestamp, order intent, and fill timestamp/price satisfy the execution contract exactly.
3. Repeated execution produces equivalent event sequences, quantities, prices, cash events, warnings, and terminal status.
4. Invalid/non-monotonic/missing-next-bar/unresolved/unsupported inputs reject before or during execution with safe codes; no partial success is reported.
5. Stable multi-instrument ordering and shared-cash precedence are deterministic, if multi-instrument v1 is supported; otherwise explicitly reject multi-instrument manifests with a documented validation error.
6. `none` cost models create explicit zero components; unsupported cost/liquidity/limit policies reject or warn exactly as contract states.
7. Lifecycle transition tests cover success, engine failure, duplicate trigger, and stale/concurrent expected status.
8. Tests prove no adapter object leaks, no external network/data access, and no durable artifact/metric behavior is added.
9. Full backend static, type, lint, format, migration/repository, and test suites pass offline.

## Acceptance criteria

- Adapter behavior follows ADR-006 and `ENGINE_EXECUTION_CONTRACT.md` exactly.
- Exact validated inputs produce deterministic, engine-neutral execution events.
- The test suite makes next-bar fill timing and absence of look-ahead bias explicit and auditable.
- Engine-specific types and defaults remain isolated in infrastructure.
- Run lifecycle is safe under duplicate/failure paths and does not falsely advertise persisted results.
- No metrics, result persistence, or unsupported execution realism appears in implementation or documentation.
- All required checks pass and handoff/status records contain only verified facts.

## Definition of done and handoff

After verification, update project memory/index and replace the following:

- Engine/Backtrader version and explicit settings:
  - `backtrader==1.9.78.123`. `Cerebro(stdstats=False)`; `broker.setcash(float(manifest.capital.amount))`; `broker.setcommission(commission=0.0)` (v1 `commission`/`tax`/`slippage` are always `none`). No `cheat_on_open`, no custom `exectype` — plain `self.buy()`/`self.close()` Market orders, which fill at the next bar's open by default (verified empirically, see `PROJECT_MEMORY.md`). A custom `bt.feed.DataBase` subclass (`_ListFeed`) feeds bars directly from an in-memory `list[NormalizedBar]` (no pandas dependency, no CSV re-read).
- Smoke-fixture timeline (`tests/test_backtrader_adapter.py::test_smoke_fixture_proves_no_look_ahead_and_next_bar_open_fill`):
  - Closes `[10, 9, 8, 12, 16, 20, 8, 4, 2, 2]`, `fast=2`/`slow=3`/`eligible_after_bars=3`. Bars 0-2: warm-up, no order possible. Bar 3 (close=12): upward crossover → BUY order **created** at bar 3's close-timestamp. Bar 4 (open=15.5): order **fills** here — asserted `!= bars[3].close`. Bar 6 (close=8): downward crossover → SELL order created at bar 6. Bar 7 (open=3.5): fills here. A second test proves repeated execution with identical inputs is event-equivalent (same sides/quantities/prices). A third proves a signal on the feed's *last* bar (no next bar) fails the whole run with `missing_next_bar`.
- Lifecycle/persistence interim policy:
  - `BacktestRunStatus` transition table (`app/domain/backtest_run.py`) extended: `created → failed` is now a legal direct transition (previously only `created → running|cancelled`), needed for pre-flight rejections that must fail before "running" is meaningful. `execute_backtest_run` (`app/application/execute_backtest_run_service.py`) validates eligibility (status must be `created`), resolves the strategy spec and verifies its checksum matches `manifest.strategy_ref.checksum`, rejects multi-instrument manifests and unresolved instrument mappings and empty bar snapshots (all → `failed` before `running`), then transitions `created → running → completed|failed`. Nothing from the run is persisted beyond the status/timestamps/failure_code already on `backtest_runs` — `ExecutionResult` (orders/fills/positions/cash/warnings) exists only in memory and is returned as **counts only** from `POST /api/v1/backtest-runs/{run_id}:execute` (no event payload, no retrievable artifact). Re-execution of a non-`created` run returns `409 conflict`.
- Commands/tests and results (from `backend/` with `.venv` active):
  - `ruff format --check .` → passed, 110 files already formatted.
  - `ruff check .` → passed, all checks passed.
  - `mypy` (strict) → passed, no issues in 109 source files (added `[[tool.mypy.overrides]] module = "backtrader.*" ignore_missing_imports = true`, same rationale as `duckdb`).
  - `pytest -q` → passed, 225 passed: adapter smoke fixture (look-ahead proof, timing, repeatability, warm-up gating, missing-next-bar failure, zero-volume-fill warning, metadata), execution-service orchestration with fakes (not-found, not-eligible, multi-instrument/unresolved-mapping/empty-snapshot pre-flight failures with correct status transitions, success path, unexpected-engine-crash path), `DuckDBBarSnapshotRepository` (resolves via `dataset_instrument_mappings`, empty-range, unresolved-mapping error), and full API contract tests for `POST .../:execute` (200 completed summary, `GET` reflects `completed` status afterward, 404 unknown run, 409 on second execute attempt, 422 for an unmapped instrument).
  - `docker compose build api` → image built successfully (added `backtrader==1.9.78.123` to `requirements.txt`). Standalone `docker run` smoke test: a full real HTTP flow (import dataset → create instrument → map it → create strategy → create run → `POST .../:execute`) against the running container returned `200 {"terminal_status":"completed","order_count":2,"fill_count":2,...}` — genuine end-to-end proof, not just mocked tests.
- Known v1 execution limitations:
  - Only one instrument per run is supported; a multi-instrument `universe.instrument_ids` is rejected outright with `unsupported_multi_instrument` (the contract's documented fallback when multi-instrument isn't implemented) — no shared-cash ordering/priority logic exists.
  - Position sizing at signal time uses the **signal bar's close** (the only price known at that moment) as the reference for `fixed_fraction` budget; the actual fill happens at the next bar's open, which can be higher or lower. If price moves up enough between signal and fill, Backtrader's own broker can legitimately reject the order for insufficient margin (`OrderStatus.REJECTED`, `rejection_reason="Margin"`) — this is correct, expected behavior for a cash-constrained fill-time price different from the sizing-time price, not a defect. Manifests with `fraction` near `1.00` are more exposed to this; there is no retry/partial-fill logic in v1.
  - Liquidity/price-limit "ignore_with_warning" currently only detects one concrete condition (`zero_volume_fill` — a fill occurring on a bar with recorded `volume == 0`); IDX-specific price-limit (ARA/ARB) data isn't modeled anywhere in the schema, so no price-limit warning can ever fire in v1 — this is an honest gap, not a silently-passing fake check.
  - No engine-level warning is raised for the position-sizing-rounds-to-zero-quantity case beyond a `position_sizing_zero_quantity` warning with no order submitted (the run still completes normally).

## Next task boundary

TASK-008 persists immutable execution artifacts, calculates documented metrics, and exposes reproducibility/audit retrieval. It may consume `ExecutionResult` but must not reinterpret engine events or alter timing semantics.
