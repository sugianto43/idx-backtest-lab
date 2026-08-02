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

export interface CreateRunFields {
  strategy_id: string;
  strategy_version: number;
  dataset_id: string;
  instrument_ids: string[];
  start_date: string;
  end_date: string;
  capital_amount: string;
  capital_currency: string;
  position_sizing_fraction: string;
  quantity_increment: string;
  money_scale: number;
  annualization_basis: number;
  risk_free_rate: string;
}

export function createRun(fields: CreateRunFields): Promise<ApiResult<BacktestRunResponse>> {
  return apiFetch<BacktestRunResponse>("/api/v1/backtest-runs", {
    method: "POST",
    json: fields,
  });
}

export interface ExecuteRunResponse {
  run_id: string;
  status: string;
  terminal_status: string;
  failure_code: string | null;
  order_count: number;
  fill_count: number;
  position_count: number;
  cash_event_count: number;
  warning_count: number;
  note: string;
}

export function executeRun(runId: string): Promise<ApiResult<ExecuteRunResponse>> {
  return apiFetch<ExecuteRunResponse>(
    `/api/v1/backtest-runs/${encodeURIComponent(runId)}:execute`,
    {
      method: "POST",
      timeoutMs: 60000,
    },
  );
}
