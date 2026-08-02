import { apiFetch } from "./client";
import type { ApiResult, PaginatedResponse } from "./types";

export interface MetricSchema {
  metric_key: string;
  status: "available" | "not_available";
  value: string | null;
  reason: string | null;
  definition_version: number;
}

export interface RunSummaryResponse {
  run_id: string;
  status: string;
  terminal_status: string | null;
  manifest_checksum: string | null;
  artifact_schema_version: number | null;
  artifact_checksum: string | null;
  event_count: number | null;
  snapshot_count: number | null;
  warning_count: number;
  metrics: MetricSchema[];
}

export interface RunArtifactsResponse {
  bundle_id: string;
  run_id: string;
  artifact_schema_version: number;
  checksum: string;
  terminal_status: string;
  provenance: Record<string, unknown>;
  event_count: number;
  snapshot_count: number;
  metric_count: number;
  created_at_utc: string;
  sections: Record<string, string>;
}

export type EventType = "order" | "fill" | "position" | "cash" | "warning";

export interface PaginatedEventsResponse {
  type: EventType;
  items: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
}

export interface PortfolioSnapshotSchema {
  sequence: number;
  timestamp_utc: string;
  cash: string;
  holdings_value: string;
  total_equity: string;
  currency: string;
  status: "valid" | "not_available";
  reason: string | null;
}

export type PortfolioSnapshotsResponse = PaginatedResponse<PortfolioSnapshotSchema>;

export interface ReproducibilityManifestResponse {
  filename: string;
  content_type: string;
  checksum: string;
  manifest: Record<string, unknown>;
}

export interface ComparisonCompatibilityResponse {
  compatible: boolean;
  reasons: string[];
}

function encodedRunId(runId: string): string {
  return encodeURIComponent(runId);
}

export function fetchRunSummary(runId: string): Promise<ApiResult<RunSummaryResponse>> {
  return apiFetch<RunSummaryResponse>(`/api/v1/backtest-runs/${encodedRunId(runId)}/summary`);
}

export function fetchRunArtifacts(runId: string): Promise<ApiResult<RunArtifactsResponse>> {
  return apiFetch<RunArtifactsResponse>(`/api/v1/backtest-runs/${encodedRunId(runId)}/artifacts`);
}

export function fetchRunEvents(
  runId: string,
  params: { type: EventType; limit: number; offset: number },
): Promise<ApiResult<PaginatedEventsResponse>> {
  return apiFetch<PaginatedEventsResponse>(
    `/api/v1/backtest-runs/${encodedRunId(runId)}/events?type=${params.type}&limit=${params.limit}&offset=${params.offset}`,
  );
}

export function fetchRunPortfolioSnapshots(
  runId: string,
  params: { limit: number; offset: number },
): Promise<ApiResult<PortfolioSnapshotsResponse>> {
  return apiFetch<PortfolioSnapshotsResponse>(
    `/api/v1/backtest-runs/${encodedRunId(runId)}/portfolio-snapshots?limit=${params.limit}&offset=${params.offset}`,
  );
}

export function fetchReproducibilityManifest(
  runId: string,
): Promise<ApiResult<ReproducibilityManifestResponse>> {
  return apiFetch<ReproducibilityManifestResponse>(
    `/api/v1/backtest-runs/${encodedRunId(runId)}/reproducibility-manifest`,
  );
}
