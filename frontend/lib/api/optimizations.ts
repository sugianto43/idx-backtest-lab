import { apiFetch } from "./client";
import type { ApiResult, PaginatedResponse } from "./types";

export const OBJECTIVE_METRIC_KEYS = [
  "initial_equity",
  "final_equity",
  "total_return",
  "annualized_return",
  "max_drawdown",
  "trade_count",
  "win_rate",
  "realized_pnl",
  "exposure_time_ratio",
] as const;

export type ObjectiveMetricKey = (typeof OBJECTIVE_METRIC_KEYS)[number];

export interface OptimizationSummary {
  optimization_id: string;
  status: string;
  dataset_id: string;
  instrument_id: string;
  base_strategy_name: string;
  objective_metric_key: string;
  candidate_count: number;
  rejected_count: number;
  max_candidate_count: number;
  failure_code: string | null;
  created_at_utc: string;
  started_at_utc: string | null;
  finished_at_utc: string | null;
}

export interface HoldoutResult {
  sealed: boolean;
  run_id: string | null;
  objective_status: string | null;
  objective_value: string | null;
  objective_reason: string | null;
}

export interface OptimizationDetail extends OptimizationSummary {
  schema_version: number;
  checksum: string;
  fast_window_grid: number[];
  slow_window_grid: number[];
  train_start: string;
  train_end: string;
  validation_start: string;
  validation_end: string;
  holdout_start: string;
  holdout_end: string;
  tie_break_rule: string;
  manifest: Record<string, unknown>;
  selected_candidate_id: string | null;
  selection_reason: string | null;
  selection_audit: Record<string, unknown>[] | null;
  selected_at_utc: string | null;
  holdout: HoldoutResult;
}

export interface OptimizationCandidate {
  candidate_id: string;
  sequence: number;
  fast_window: number;
  slow_window: number;
  status: string;
  rejection_reason: string | null;
  strategy_id: string | null;
  strategy_version: number | null;
  train_run_id: string | null;
  validation_run_id: string | null;
  objective_status: string | null;
  objective_value: string | null;
  objective_reason: string | null;
  warning_count: number;
  created_at_utc: string;
}

export type OptimizationListResponse = PaginatedResponse<OptimizationSummary>;
export type OptimizationCandidatesResponse = PaginatedResponse<OptimizationCandidate>;

export function fetchOptimizations(params: {
  limit: number;
  offset: number;
}): Promise<ApiResult<OptimizationListResponse>> {
  return apiFetch<OptimizationListResponse>(
    `/api/v1/optimizations?limit=${params.limit}&offset=${params.offset}`,
  );
}

export function fetchOptimization(optimizationId: string): Promise<ApiResult<OptimizationDetail>> {
  return apiFetch<OptimizationDetail>(
    `/api/v1/optimizations/${encodeURIComponent(optimizationId)}`,
  );
}

export function fetchOptimizationCandidates(
  optimizationId: string,
  params: { limit: number; offset: number },
): Promise<ApiResult<OptimizationCandidatesResponse>> {
  return apiFetch<OptimizationCandidatesResponse>(
    `/api/v1/optimizations/${encodeURIComponent(optimizationId)}/candidates?limit=${params.limit}&offset=${params.offset}`,
  );
}

export interface CreateOptimizationFields {
  dataset_id: string;
  instrument_id: string;
  base_strategy_name: string;
  fast_windows: number[];
  slow_windows: number[];
  train_start: string;
  train_end: string;
  validation_start: string;
  validation_end: string;
  holdout_start: string;
  holdout_end: string;
  capital_amount: string;
  capital_currency: string;
  position_sizing_fraction: string;
  quantity_increment: string;
  money_scale: number;
  annualization_basis: number;
  risk_free_rate: string;
  objective_metric_key: ObjectiveMetricKey;
}

export function createOptimization(
  fields: CreateOptimizationFields,
): Promise<ApiResult<OptimizationDetail>> {
  return apiFetch<OptimizationDetail>("/api/v1/optimizations", {
    method: "POST",
    json: fields,
  });
}

export function executeOptimization(
  optimizationId: string,
): Promise<ApiResult<OptimizationDetail>> {
  return apiFetch<OptimizationDetail>(
    `/api/v1/optimizations/${encodeURIComponent(optimizationId)}:execute`,
    { method: "POST", timeoutMs: 60000 },
  );
}
