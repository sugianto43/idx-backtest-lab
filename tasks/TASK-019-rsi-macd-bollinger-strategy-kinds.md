# TASK-019 — RSI, MACD, and Bollinger Band strategy kinds

## Objective

Per the user's explicit request for "strategies usable by professional traders," add three new declarative strategy kinds — `rsi_threshold`, `macd_crossover`, `bollinger_breakout` — alongside the existing `sma_crossover`, following the identical fixed/deterministic/long-only/single-signal shape. See ADR-012 for the full design and rationale, including why a free-form custom-code strategy editor was explicitly ruled out.

## Required reading

Read `.claude/CLAUDE.md`, `docs/adr/ADR-012-additional-strategy-kinds.md`, `docs/adr/ADR-005-declarative-strategy-specification.md` (or the closest ADR describing the v1 strategy schema), TASK-006, TASK-007, and this task.

## Dependencies

TASK-006 (backtest domain model) and TASK-007 (Backtrader engine adapter) must be complete (they are).

## In scope

- `backend/app/domain/strategy_spec.py`: `RsiThresholdParameters`, `MacdCrossoverParameters`, `BollingerBreakoutParameters` dataclasses (validation + `to_canonical_dict()` + `required_warmup_bars()`), `build_parameters(kind, raw)` factory, `StrategySpecV1` kind/parameters-type consistency check.
- `backend/migrations/0007_expand_strategy_kinds.sql`: widen the `strategy_specs.kind` CHECK constraint via DuckDB's rename/recreate/copy/drop pattern.
- `backend/app/application/strategy_spec_service.py`: `create_strategy_spec` takes a generic `parameters: Mapping[str, object]` instead of SMA-specific kwargs.
- `backend/app/application/execute_optimization_service.py`: updated call site (still `sma_crossover`-only; optimization is not extended to the new kinds).
- `backend/app/infrastructure/db/strategy_spec_repository.py`: `_row_to_spec` dispatches parameter construction via `build_parameters`.
- `backend/app/api/schemas/strategies.py` / `routes/strategies.py`: generic `dict[str, Any]` parameters in request/response; domain remains the single source of parameter validation.
- `backend/app/infrastructure/engine/backtrader_adapter.py`: shared `_BaseCrossoverStrategy` plus one thin subclass per kind; `BacktraderEngineAdapter.execute` dispatches by `strategy.kind`.
- Frontend: `lib/api/strategies.ts` generalized to a `STRATEGY_KINDS` config table (fields, defaults, warm-up formula per kind); `/strategies/new` gains a kind selector with dynamic parameter fields; `/strategies` list and `/strategies/{id}/versions/{version}` detail pages render parameters generically instead of hardcoded SMA fields.
- Tests: domain validation tests per new parameter type, API tests creating each new kind, Backtrader adapter smoke tests proving each kind enters/exits correctly, frontend tests for the new kind-selector form.

## Out of scope

- A custom/combination strategy kind (tracked as TASK-020).
- Extending the optimization framework to any kind other than `sma_crossover`.
- Any free-form, user-authored, or executable strategy code — explicitly excluded per ADR-012 and the prior TASK-011/TASK-012 exclusions.

## Test plan

1. Backend: `ruff format --check`, `ruff check`, `mypy`, `pytest -q` all clean; new domain/API/engine tests cover validation rejection paths and a full entry+exit signal for each new kind.
2. Frontend: `npm run format`/`lint`/`type-check`/`test`/`build` all clean; new tests cover kind switching, per-kind field validation, and payload shape per kind.
3. Manual: create one strategy of each kind via the API and confirm `GET .../versions/1` round-trips the exact parameters.

## Acceptance criteria

- Four strategy kinds are creatable and independently backtestable; each kind's entry/exit rule is documented in ADR-012 and matches its engine implementation.
- No kind requires or accepts arbitrary user code.
- All quality checks pass.

## Definition of done and handoff

After verification, update `.claude/PROJECT_MEMORY.md` and `.claude/TASK_INDEX.md` recording: the four kinds and their entry/exit rules, the `build_parameters` dispatch pattern, the migration 0007 rename/recreate pattern (and why DuckDB required it), and command/test results.

## Next task boundary

TASK-020 (custom multi-indicator combination kind) and TASK-021 (picker-based creation UX for runs/optimizations/strategies) are separate follow-ups from the same user request.
