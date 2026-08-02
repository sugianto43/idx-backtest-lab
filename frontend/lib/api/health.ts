import { apiFetch } from "./client";
import type { ApiResult } from "./types";

export interface LivenessResponse {
  status: "ok";
}

export interface ReadinessResponse {
  status: "ok";
  service: string;
  version: string;
  database: "ready";
}

/** `/health` is permitted only for system liveness display, never product data. */
export function fetchLiveness(options?: {
  timeoutMs?: number;
}): Promise<ApiResult<LivenessResponse>> {
  return apiFetch<LivenessResponse>("/health", options);
}

export function fetchReadiness(options?: {
  timeoutMs?: number;
}): Promise<ApiResult<ReadinessResponse>> {
  return apiFetch<ReadinessResponse>("/api/v1/ready", options);
}
