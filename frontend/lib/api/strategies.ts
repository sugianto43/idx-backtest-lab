import { apiFetch } from "./client";
import type { ApiResult, PaginatedResponse } from "./types";

export type StrategyKind =
  "sma_crossover" | "rsi_threshold" | "macd_crossover" | "bollinger_breakout";

export interface SignalPolicy {
  signal_time: "bar_close";
  eligible_after_bars: number;
  long_only: boolean;
}

export interface StrategySpecResponse {
  strategy_id: string;
  version: number;
  schema_version: number;
  name: string;
  kind: string;
  parameters: Record<string, number | string>;
  signal_policy: SignalPolicy;
  checksum: string;
  created_at_utc: string;
}

export type StrategySpecListResponse = PaginatedResponse<StrategySpecResponse>;

export function fetchStrategies(params: {
  limit: number;
  offset: number;
}): Promise<ApiResult<StrategySpecListResponse>> {
  return apiFetch<StrategySpecListResponse>(
    `/api/v1/strategies?limit=${params.limit}&offset=${params.offset}`,
  );
}

export function fetchStrategyVersion(
  strategyId: string,
  version: number,
): Promise<ApiResult<StrategySpecResponse>> {
  return apiFetch<StrategySpecResponse>(
    `/api/v1/strategies/${encodeURIComponent(strategyId)}/versions/${version}`,
  );
}

export interface StrategyKindField {
  key: string;
  label: string;
  help: string;
  defaultValue: number;
  min: number;
}

export interface StrategyKindConfig {
  value: StrategyKind;
  label: string;
  description: string;
  fields: StrategyKindField[];
  /** Mirrors the backend's `required_warmup_bars()` per parameter dataclass (domain source of truth). */
  requiredWarmupBars: (parameters: Record<string, number>) => number;
}

export const STRATEGY_KINDS: StrategyKindConfig[] = [
  {
    value: "sma_crossover",
    label: "SMA Crossover",
    description:
      "Enters long when the fast simple moving average crosses above the slow one; exits on a downward crossover.",
    fields: [
      {
        key: "fast_window",
        label: "Fast window (bars)",
        help: "Smaller than the slow window.",
        defaultValue: 10,
        min: 1,
      },
      {
        key: "slow_window",
        label: "Slow window (bars)",
        help: "Larger than the fast window.",
        defaultValue: 30,
        min: 1,
      },
    ],
    requiredWarmupBars: (p) => p.slow_window,
  },
  {
    value: "rsi_threshold",
    label: "RSI Threshold",
    description:
      "Enters long when RSI crosses up through the oversold threshold; exits when RSI crosses back down through the overbought threshold.",
    fields: [
      {
        key: "period",
        label: "RSI period (bars)",
        help: "Number of bars used to compute RSI.",
        defaultValue: 14,
        min: 2,
      },
      {
        key: "oversold_threshold",
        label: "Oversold threshold",
        help: "0-100; must be less than the overbought threshold.",
        defaultValue: 30,
        min: 1,
      },
      {
        key: "overbought_threshold",
        label: "Overbought threshold",
        help: "0-100; must be greater than the oversold threshold.",
        defaultValue: 70,
        min: 1,
      },
    ],
    requiredWarmupBars: (p) => p.period + 1,
  },
  {
    value: "macd_crossover",
    label: "MACD Crossover",
    description:
      "Enters long when the MACD line crosses above its signal line; exits on a downward crossover.",
    fields: [
      {
        key: "fast_period",
        label: "Fast EMA period (bars)",
        help: "Smaller than the slow period.",
        defaultValue: 12,
        min: 1,
      },
      {
        key: "slow_period",
        label: "Slow EMA period (bars)",
        help: "Larger than the fast period.",
        defaultValue: 26,
        min: 1,
      },
      {
        key: "signal_period",
        label: "Signal EMA period (bars)",
        help: "Smoothing period for the signal line.",
        defaultValue: 9,
        min: 1,
      },
    ],
    requiredWarmupBars: (p) => p.slow_period + p.signal_period,
  },
  {
    value: "bollinger_breakout",
    label: "Bollinger Breakout",
    description:
      "Enters long when price breaks above the upper Bollinger Band; exits when price falls back below the middle band.",
    fields: [
      {
        key: "period",
        label: "Moving average period (bars)",
        help: "Number of bars used for the band basis.",
        defaultValue: 20,
        min: 2,
      },
      {
        key: "num_std_dev",
        label: "Standard deviations",
        help: "Whole number, 1-4.",
        defaultValue: 2,
        min: 1,
      },
    ],
    requiredWarmupBars: (p) => p.period,
  },
];

export function strategyKindConfig(kind: string): StrategyKindConfig | undefined {
  return STRATEGY_KINDS.find((k) => k.value === kind);
}

/** Human-readable one-line summary of a strategy's parameters for list views. */
export function summarizeParameters(
  kind: string,
  parameters: Record<string, number | string>,
): string {
  const config = strategyKindConfig(kind);
  if (!config) return JSON.stringify(parameters);
  return config.fields
    .map((field) => `${field.label.split(" (")[0]}=${parameters[field.key]}`)
    .join(", ");
}

export interface CreateStrategyFields {
  name: string;
  kind: StrategyKind;
  parameters: Record<string, number | string>;
  eligibleAfterBars: number;
}

/**
 * `price_field`, `signal_time`, and `long_only` are v1-fixed, not user-chosen.
 * `eligible_after_bars` is derived from the kind's required warm-up (never a free-form input),
 * matching the established convention that warm-up-driven fields are computed, not typed in.
 */
export function createStrategy(
  fields: CreateStrategyFields,
): Promise<ApiResult<StrategySpecResponse>> {
  return apiFetch<StrategySpecResponse>("/api/v1/strategies", {
    method: "POST",
    json: {
      name: fields.name,
      kind: fields.kind,
      parameters: { ...fields.parameters, price_field: "close" },
      signal_policy: {
        signal_time: "bar_close",
        eligible_after_bars: fields.eligibleAfterBars,
        long_only: true,
      },
    },
  });
}
