# ADR-013: Custom multi-indicator combination strategy kind

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

ADR-012 added three indicator-based strategy kinds but explicitly deferred "custom" combinations of them to a follow-up, since combining multiple conditions is a materially different feature (rule composition) rather than "one more indicator." The user's original request explicitly asked for the ability to "build custom" strategies too, clarified (via the same AskUserQuestion exchange that produced ADR-012) to mean combining configurable indicator conditions — never free-form or executable code.

## Decision

Add a fifth strategy kind, `multi_indicator_combo`, whose parameters are 2 or 3 **conditions**, each an existing base kind (`sma_crossover`, `rsi_threshold`, `macd_crossover`, `bollinger_breakout`) with its own parameters. The combination rule is fixed and deterministic, not user-authored:

- **Entry** requires every condition's entry signal to be true on the same bar (AND).
- **Exit** fires when any one condition's exit signal is true (OR) — deliberately asymmetric: harder to get in, easier to get out, which is the conservative default for a combined signal.

Conditions must use distinct base kinds (no duplicate-kind conditions in v1 — avoids ambiguity about combining, say, two differently-parameterized SMA crossovers, which is a reasonable future extension but out of scope here).

Domain (`app/domain/strategy_spec.py`): `ComboCondition` (kind + one of the four base parameter dataclasses, validated for kind/type consistency) and `MultiIndicatorComboParameters` (2-3 distinct-kind conditions, `required_warmup_bars()` = max across conditions). `build_parameters` gained a special case for `multi_indicator_combo`'s nested `{"conditions": [{"kind", "parameters"}, ...]}` shape, recursing into itself for each condition's parameters — this is the only kind whose raw payload isn't a flat dict of scalars.

Engine (`app/infrastructure/engine/backtrader_adapter.py`): refactored so every base kind's indicator-building logic lives in one shared `_build_signal_lines(data, kind, params) -> (entry_line, exit_line)` function, used both by each single-kind strategy class and by the new `_MultiIndicatorComboStrategy` (which builds one signal-line pair per condition and combines them with `all()`/`any()`). This guarantees a condition inside a combo behaves identically to that same kind used standalone — no duplicated or drifted logic.

Migration `0008_add_multi_indicator_combo_kind.sql` widens the `strategy_specs.kind` CHECK constraint again, via the same DuckDB rename/recreate/copy/drop pattern ADR-012 established.

## Consequences

- Users can build strategies like "SMA crossover AND RSI oversold bounce" without any code, satisfying the "custom" part of the original request while staying inside the no-arbitrary-code boundary from ADR-012/TASK-011/TASK-012.
- The frontend's `/strategies/new` form grew a distinct combo-building UI (a repeatable 2-3 condition list, each with its own indicator picker and that indicator's fields) rather than trying to force the flat single-kind form to also describe a combo.
- Parameter optimization (grid search) is still not extended to any kind beyond `sma_crossover` — unchanged from ADR-012's scope decision.
- A combo's `required_warmup_bars()` uses the *slowest* condition's warm-up, which can be conservative (a fast condition inside the combo becomes ready before the combo as a whole is allowed to signal) — this is intentional: it guarantees every condition's indicator has real data before any combo signal is evaluated.

## Reversibility

High. `multi_indicator_combo` is additive: removing it deletes one dataclass pair, one `build_parameters` branch, one engine strategy class, and its dispatch table entry, without touching any of the four base kinds' own behavior (proven by the fact that the pre-existing SMA/RSI/MACD/Bollinger tests all still pass unmodified after the engine's `_build_signal_lines` refactor).
