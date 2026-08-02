# TASK-020 — Custom multi-indicator combination strategy kind

## Objective

Add the `multi_indicator_combo` strategy kind: a user-composed combination of 2-3 existing base indicator conditions (AND to enter, OR to exit), satisfying the "custom strategy" part of the user's original request without introducing any free-form or executable strategy code. See ADR-013.

## Required reading

Read `.claude/CLAUDE.md`, `docs/adr/ADR-013-multi-indicator-combo-strategy-kind.md`, `docs/adr/ADR-012-additional-strategy-kinds.md`, TASK-019, and this task.

## Dependencies

TASK-019 (RSI/MACD/Bollinger strategy kinds) must be complete (it is) — the combo kind reuses its four base kinds' parameter dataclasses and engine indicator logic.

## In scope

- `backend/app/domain/strategy_spec.py`: `ComboCondition`, `MultiIndicatorComboParameters`, the `multi_indicator_combo` branch in `build_parameters` (nested `{"conditions": [...]}` parsing), `BASE_STRATEGY_KINDS`/`MIN_COMBO_CONDITIONS`/`MAX_COMBO_CONDITIONS` constants.
- `backend/migrations/0008_add_multi_indicator_combo_kind.sql`: widen the `kind` CHECK constraint again.
- `backend/app/infrastructure/engine/backtrader_adapter.py`: extract `_build_signal_lines` shared by every single-kind strategy class and the new `_MultiIndicatorComboStrategy` (AND entry / OR exit over its conditions' signal lines).
- Frontend: `lib/api/strategies.ts` gains `BaseStrategyKind`/`MIN_COMBO_CONDITIONS`/`MAX_COMBO_CONDITIONS` and combo-aware `summarizeParameters`; `/strategies/new` gains a distinct combo-building UI (repeatable condition list, each with its own indicator picker); the strategy detail page renders combo conditions instead of flat fields.
- Tests: domain validation (condition count/duplicate-kind/kind-type-mismatch rejections), API creation test for a combo strategy, an engine smoke test proving AND-entry across two real conditions, frontend tests for the combo UI (default two conditions, add/remove within bounds, duplicate-kind rejection, submitted payload shape).

## Out of scope

- Combining more than 3 conditions, or two conditions of the same base kind.
- Extending optimization (grid search) to any kind other than `sma_crossover`.
- Any free-form, user-authored, or executable strategy code.

## Test plan

1. Backend: `ruff format --check`, `ruff check`, `mypy`, `pytest -q` all clean; combo-specific tests cover both rejection paths and a real entry+exit signal.
2. Frontend: `npm run format`/`lint`/`type-check`/`test`/`build` all clean.
3. Manual: create a combo strategy via the API combining `sma_crossover` and `rsi_threshold`, confirm `GET .../versions/1` round-trips both conditions exactly.

## Acceptance criteria

- A combo strategy is creatable, independently backtestable, and its AND/OR semantics match ADR-013.
- No duplicate-kind or single-condition combo is accepted.
- All quality checks pass.

## Definition of done and handoff

After verification, update `.claude/PROJECT_MEMORY.md` and `.claude/TASK_INDEX.md` recording: the combo kind's AND-entry/OR-exit rule, the `_build_signal_lines` engine refactor and why it guarantees condition/standalone parity, the migration 0008 pattern, and command/test results.

## Next task boundary

TASK-021 (picker-based creation UX for runs/optimizations/strategies) is the last item from the same user request.
