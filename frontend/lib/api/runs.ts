import { apiFetch } from "./client";
import type { ApiResult, MetricValue, PaginatedResponse } from "./types";

export interface BacktestRunResponse {
  run_id: string;
  dataset_id: string;
  strategy_id: string | null;
  strategy_version: number | null;
  schema_version: number | null;
  status: string;
  manifest_checksum: string | null;
  manifest: Record<string, unknown>;
  warning_count: number;
  created_at_utc: string;
  final_equity: MetricValue;
  total_return: MetricValue;
}

export type BacktestRunListResponse = PaginatedResponse<BacktestRunResponse>;

export function fetchRuns(params: {
  limit: number;
  offset: number;
}): Promise<ApiResult<BacktestRunListResponse>> {
  return apiFetch<BacktestRunListResponse>(
    `/api/v1/backtest-runs?limit=${params.limit}&offset=${params.offset}`,
  );
}

export function fetchRun(runId: string): Promise<ApiResult<BacktestRunResponse>> {
  return apiFetch<BacktestRunResponse>(`/api/v1/backtest-runs/${encodeURIComponent(runId)}`);
}
