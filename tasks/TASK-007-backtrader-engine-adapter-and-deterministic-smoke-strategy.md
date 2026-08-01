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
- Smoke-fixture timeline:
- Lifecycle/persistence interim policy:
- Commands/tests and results:
- Known v1 execution limitations:

## Next task boundary

TASK-008 persists immutable execution artifacts, calculates documented metrics, and exposes reproducibility/audit retrieval. It may consume `ExecutionResult` but must not reinterpret engine events or alter timing semantics.
