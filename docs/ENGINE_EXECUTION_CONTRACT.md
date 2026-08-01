# Engine Execution Contract

## Input boundary

The engine adapter accepts a validated Run Manifest v1, exact resolved instruments, and an immutable dataset-bar snapshot. It rejects any input that has not passed TASK-006 validation, contains unresolved identities, has non-monotonic bars, lacks the required next bar for an eligible signal, or requests unsupported execution behavior.

## v1 timing semantics

1. At the close of bar **t**, the strategy reads only bars through **t**.
2. A crossover signal is eligible only after `slow_window` completed bars.
3. The signal creates an order intent timestamped at the close of **t**.
4. A filled order executes at the open of the next eligible bar **t+1**.
5. The adapter never fills an order on bar **t** using a close-derived signal.
6. If the next bar is unavailable, behavior follows `missing_next_bar_policy`; v1 allows only `reject`.

## v1 strategy/execution semantics

- `sma_crossover` compares prior/current fast and slow simple moving averages calculated from declared `close` values.
- Long-only: an upward crossover enters a long position; a downward crossover exits an existing long position. No short order is created.
- Position sizing is `fixed_fraction` of available cash, constrained by integer quantity increment and explicit monetary rounding.
- Commission, tax, and slippage are v1 `none` only. Liquidity and price-limit policies are `ignore_with_warning` only, producing a run warning if a relevant condition is detectable; they never silently claim realistic execution.
- Corporate-action treatment is `dataset_as_declared_no_event_adjustment`; the adapter does not transform bars or holdings.
- Multiple instruments are processed in a deterministic stable order by `instrument_id`; shared-cash order priority is that same order and must be recorded in execution metadata.

## Product-neutral output

The adapter returns an in-memory `ExecutionResult` with no Backtrader objects:

| Item | Required contents |
| --- | --- |
| `execution_metadata` | adapter name/version, manifest checksum, dataset checksum, deterministic ordering policy, started/finished timestamps, event count. |
| `order_events` | opaque order ID, instrument ID, side, created timestamp, intended quantity, status transitions, rejection reason if any. |
| `fill_events` | order ID, instrument ID, side, fill timestamp, quantity, price, fee/tax/slippage components, currency, rounding details. |
| `position_events` | timestamp, instrument ID, quantity, average cost, reason. |
| `cash_events` | timestamp, currency, before/after values, reason. |
| `warnings` | stable warning code, safe message, related instrument/time where applicable. |
| `terminal_status` | `completed` or `failed`, plus safe failure code. |

The output does not include calculated performance metrics, charts, persisted artifacts, or a UI-facing response. TASK-008 owns those concerns.

## Determinism requirements

- Stable input order, decimal rounding, timestamps, IDs/test generators, and broker configuration.
- No network, wall-clock dependency in calculation, implicit random seed, locale dependency, or external data fetch.
- Equivalent canonical manifest and bar snapshot yield event-equivalent output; diagnostic timestamps may use an injected clock and must not affect semantic comparison.
- Engine exceptions map to product-neutral safe failure codes with retained internal diagnostic context for logs only.
