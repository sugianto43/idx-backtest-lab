/**
 * Shared typed API transport models. Decimal-bearing fields are always
 * `string` here and must never be parsed into `number` for calculation.
 */

export interface ApiErrorBody {
  code: string;
  message: string;
  details: unknown[];
  correlation_id: string;
}

export type ApiErrorKind =
  "config_error" | "network_error" | "timeout" | "malformed_response" | "api_error";

export interface ApiError {
  kind: ApiErrorKind;
  message: string;
  code?: string;
  correlationId?: string;
  status?: number;
  details?: unknown[];
}

export type ApiResult<T> =
  { ok: true; data: T; correlationId?: string } | { ok: false; error: ApiError };

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

/** A metric or run-summary financial value: never a raw number. */
export interface MetricValue {
  status: "available" | "not_available";
  value: string | null;
  reason: string | null;
}
