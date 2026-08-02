import { apiFetch } from "./client";
import type { ApiResult, PaginatedResponse } from "./types";

export interface SmaCrossoverParameters {
  fast_window: number;
  slow_window: number;
  price_field: "close";
}

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
  parameters: SmaCrossoverParameters;
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

export interface CreateStrategyFields {
  name: string;
  fastWindow: number;
  slowWindow: number;
}

/**
 * Sends exactly the v1 sma_crossover contract payload. `price_field`,
 * `signal_time`, and `long_only` are v1-fixed, not user-chosen; per the UX
 * contract, `eligible_after_bars` mirrors `slow_window` (the warm-up
 * period) rather than being a separate free-form input.
 */
export function createStrategy(
  fields: CreateStrategyFields,
): Promise<ApiResult<StrategySpecResponse>> {
  return apiFetch<StrategySpecResponse>("/api/v1/strategies", {
    method: "POST",
    json: {
      name: fields.name,
      kind: "sma_crossover",
      parameters: {
        fast_window: fields.fastWindow,
        slow_window: fields.slowWindow,
        price_field: "close",
      },
      signal_policy: {
        signal_time: "bar_close",
        eligible_after_bars: fields.slowWindow,
        long_only: true,
      },
    },
  });
}
