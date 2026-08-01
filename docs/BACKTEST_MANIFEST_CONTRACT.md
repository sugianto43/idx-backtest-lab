# Strategy Specification and Backtest Manifest Contract

## Principles

A strategy specification describes intent. A run manifest describes one immutable simulation request after all defaults have been resolved. Both use canonical JSON, a positive `schema_version`, opaque IDs, and a checksum generated from their canonical content. Persisted documents are never edited.

## Strategy specification v1

The initial built-in strategy vocabulary is deliberately small: `sma_crossover` only. It is a declarative rule, not executable Python.

```json
{
  "schema_version": 1,
  "strategy_id": "opaque-id",
  "version": 1,
  "name": "SMA crossover 10/30",
  "kind": "sma_crossover",
  "parameters": {
    "fast_window": 10,
    "slow_window": 30,
    "price_field": "close"
  },
  "signal_policy": {
    "signal_time": "bar_close",
    "eligible_after_bars": 30,
    "long_only": true
  },
  "created_at_utc": "2026-08-01T00:00:00Z"
}
```

Validation requires positive integer windows, `fast_window < slow_window`, supported price field, `eligible_after_bars >= slow_window`, and all declared fields. Strategy v1 cannot express short selling, leverage, intrabar signals, custom indicators, or arbitrary code.

## Run manifest v1

```json
{
  "schema_version": 1,
  "run_id": "opaque-id",
  "strategy_ref": {"strategy_id": "opaque-id", "version": 1, "checksum": "sha256:..."},
  "dataset_ref": {"dataset_id": "opaque-id", "content_checksum": "sha256:..."},
  "universe": {"instrument_ids": ["opaque-id"], "unresolved_identifier_policy": "reject"},
  "period": {"start_date": "2020-01-01", "end_date": "2024-12-31", "bar_interval": "1d"},
  "capital": {"amount": "100000000.00", "currency": "IDR"},
  "signal_and_fill": {"signal_time": "bar_close", "fill_time": "next_bar_open", "missing_next_bar_policy": "reject"},
  "corporate_action_treatment": "dataset_as_declared_no_event_adjustment",
  "execution": {
    "position_sizing": {"kind": "fixed_fraction", "fraction": "1.00"},
    "commission": {"kind": "none"},
    "tax": {"kind": "none"},
    "slippage": {"kind": "none"},
    "liquidity": {"kind": "ignore_with_warning"},
    "price_limit": {"kind": "ignore_with_warning"},
    "rounding": {"quantity_increment": "1", "money_scale": 2}
  },
  "benchmark": {"kind": "none"},
  "metrics": {"annualization_basis": 252, "risk_free_rate": "0.00"},
  "engine_ref": {"adapter_name": "backtrader", "adapter_version": "unimplemented"},
  "created_at_utc": "2026-08-01T00:00:00Z"
}
```

## Validation rules

- All referenced dataset/instrument/strategy versions must exist, be immutable, and be eligible; unresolved identifiers reject a run.
- Start/end dates must be ordered and inside the dataset’s known coverage.
- Dataset interval must equal requested interval; no resampling is implicit.
- Capital amount is a positive decimal string; currency must be explicit and supported by data/strategy policy.
- Signal/fill timing is fixed to `bar_close` → `next_bar_open` in v1. Same-bar fills and intrabar decisions are rejected.
- Every execution/cost/liquidity/limit/rounding field is required even when its value is `none` or warning-only.
- Adjustment treatment must match the referenced dataset’s declared adjustment policy. The v1 setting records this fact; it does not apply an event transformation.
- Metric settings are metadata only until TASK-008; their formulas and basis are persisted now to prevent future ambiguity.

## Compatibility

Unknown schema versions or unknown enum values reject with stable validation errors. New fields require a new schema version or explicit backward-compatible rule with contract tests. Checksums use a documented canonical JSON serialization: sorted object keys, UTF-8, no insignificant whitespace, and normalized decimal strings.
