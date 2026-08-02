import { resolveApiBaseUrl } from "./config";
import type { ApiErrorBody, ApiResult } from "./types";

const CORRELATION_ID_HEADER = "X-Correlation-Id";
const DEFAULT_TIMEOUT_MS = 8000;

function isApiErrorBody(value: unknown): value is { error: ApiErrorBody } {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }
  const candidate = (value as { error: unknown }).error;
  return (
    typeof candidate === "object" &&
    candidate !== null &&
    "code" in candidate &&
    "message" in candidate &&
    "correlation_id" in candidate
  );
}

export interface ApiFetchOptions {
  timeoutMs?: number;
  signal?: AbortSignal;
  method?: "GET" | "POST";
  body?: FormData;
  json?: unknown;
}

/**
 * The single transport function every typed API call goes through. Callers
 * never issue raw `fetch` calls against the product API.
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<ApiResult<T>> {
  const config = resolveApiBaseUrl();
  if (!config.ok) {
    return { ok: false, error: { kind: "config_error", message: config.reason } };
  }

  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  options.signal?.addEventListener("abort", () => controller.abort());

  const headers: Record<string, string> = { Accept: "application/json" };
  let requestBody: BodyInit | undefined = options.body;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    requestBody = JSON.stringify(options.json);
  }

  let response: Response;
  try {
    response = await fetch(`${config.baseUrl}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: requestBody,
      signal: controller.signal,
    });
  } catch (cause) {
    clearTimeout(timeoutId);
    if (cause instanceof DOMException && cause.name === "AbortError") {
      return {
        ok: false,
        error: { kind: "timeout", message: "The request timed out. Please try again." },
      };
    }
    return {
      ok: false,
      error: {
        kind: "network_error",
        message: "Could not reach the API. Check your connection and try again.",
      },
    };
  } finally {
    clearTimeout(timeoutId);
  }

  const correlationId = response.headers.get(CORRELATION_ID_HEADER) ?? undefined;

  const rawText = await response.text();
  let parsed: unknown;
  try {
    parsed = rawText.length > 0 ? JSON.parse(rawText) : undefined;
  } catch {
    return {
      ok: false,
      error: {
        kind: "malformed_response",
        message: "The API returned a response that could not be understood.",
        status: response.status,
        correlationId,
      },
    };
  }

  if (!response.ok) {
    if (isApiErrorBody(parsed)) {
      return {
        ok: false,
        error: {
          kind: "api_error",
          message: parsed.error.message,
          code: parsed.error.code,
          correlationId: parsed.error.correlation_id || correlationId,
          status: response.status,
          details: parsed.error.details,
        },
      };
    }
    return {
      ok: false,
      error: {
        kind: "malformed_response",
        message: "The API returned an unexpected error response.",
        status: response.status,
        correlationId,
      },
    };
  }

  return { ok: true, data: parsed as T, correlationId };
}
