# ADR-012: RSI, MACD, and Bollinger Band strategy kinds

- **Status:** Accepted
- **Date:** 2026-08-02

## Context

Through TASK-017, the only strategy kind the product could express was `sma_crossover` (ADR-005/TASK-006's declarative v1 schema). The user explicitly asked for "a selection of strategies usable by professional traders," and, when asked to clarify the scope, chose adding common indicator-based strategy kinds (RSI, MACD, Bollinger Bands) with a later custom-combination kind, rather than a free-form code/script strategy editor — the latter was explicitly ruled out because it would conflict with TASK-011/TASK-012's prior exclusion of arbitrary executable strategy code, and this product has no sandboxing or auth to make that safe.

## Decision

Add three new strategy kinds alongside `sma_crossover`, each a fixed, deterministic, long-only, single-signal rule — identical in shape to `sma_crossover` (one entry condition, one exit condition, `bar_close` signal timing, `next_bar_open` fills), differing only in which indicator and threshold/crossover rule drives the signal:

- `rsi_threshold` — RSI(`period`); enters when RSI crosses up through `oversold_threshold`, exits when RSI crosses back down through `overbought_threshold`.
- `macd_crossover` — MACD(`fast_period`, `slow_period`, `signal_period`); enters when the MACD line crosses above its signal line, exits on a downward crossover.
- `bollinger_breakout` — Bollinger Bands(`period`, `num_std_dev`); enters when price breaks above the upper band, exits when price falls back below the middle band.

Domain layer (`app/domain/strategy_spec.py`): each kind gets its own frozen parameter dataclass with its own validation and a `required_warmup_bars()` method (replacing the old SMA-only `eligible_after_bars >= slow_window` check with a per-kind warm-up requirement). A `build_parameters(kind, raw)` factory dispatches raw dict input to the correct dataclass and is the single place kind validity is checked; `StrategySpecV1` verifies the parameters object's concrete type matches its declared `kind`.

API layer: `CreateStrategyRequest`/`StrategySpecResponse.parameters` become `dict[str, Any]` instead of a kind-specific Pydantic model — the domain factory is the single source of parameter validation (avoids duplicating per-kind validation in two layers), and the route still returns `422 validation_error` with the same error envelope for any invalid kind or parameter combination.

Engine layer (`app/infrastructure/engine/backtrader_adapter.py`): the previously monolithic `_SmaCrossoverStrategy` is split into a shared `_BaseCrossoverStrategy` (all order submission, fill accounting, warning, and audit-trail machinery) plus one thin subclass per kind that only builds its own Backtrader indicators and implements `_entry_signal()`/`_exit_signal()`. `BacktraderEngineAdapter.execute` dispatches to the right subclass by `strategy.kind`.

Migration `0007_expand_strategy_kinds.sql` recreates `strategy_specs` (DuckDB does not support `ALTER TABLE ... DROP/ADD CONSTRAINT`, so the standard workaround is rename-old / create-new-with-desired-schema / copy-rows / drop-old) to widen the `kind` `CHECK` constraint to the four supported values; no other table references `strategy_specs` by foreign key, so this is a safe, data-preserving rename-and-copy.

The parameter-optimization framework (TASK-012/ADR-009) is **not** extended to the new kinds in this task — it remains `sma_crossover`-specific (a grid over `fast_window`/`slow_window`). Extending optimization to other kinds is a separate, later decision if requested.

## Consequences

- Users can now build strategies around four well-known indicator families instead of one, without any arbitrary/executable code path — every kind is a fixed, auditable, backtested rule.
- `strategy_spec_service.create_strategy_spec`'s signature changed from individual `fast_window`/`slow_window`/`price_field` keyword arguments to a single `parameters: Mapping[str, object]` — the optimization service's call site was updated to pass a dict instead of separate kwargs.
- A "custom" strategy (combining multiple indicator conditions) is explicitly deferred to a follow-up task/ADR — it is a materially different composition feature (AND/OR over multiple base conditions) rather than "one more indicator," and is scoped separately to keep this change reviewable.

## Reversibility

High for the three new kinds themselves (each is an isolated dataclass + engine subclass; deleting one removes exactly its dataclass, subclass, and dispatch entry). Moderate for the migration — recreating `strategy_specs` again to narrow the `kind` constraint back would require the same rename/copy pattern, and any already-persisted strategy of a removed kind would need a data migration decision at that time.
