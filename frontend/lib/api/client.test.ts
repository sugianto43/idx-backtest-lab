import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";

const ORIGINAL = process.env.NEXT_PUBLIC_API_BASE_URL;

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
});

afterEach(() => {
  if (ORIGINAL === undefined) {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  } else {
    process.env.NEXT_PUBLIC_API_BASE_URL = ORIGINAL;
  }
  vi.unstubAllGlobals();
});

function jsonResponse(
  body: unknown,
  init: { status?: number; headers?: Record<string, string> } = {},
) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
}

describe("apiFetch", () => {
  it("returns a config_error without calling fetch when the base URL is unset", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await apiFetch("/health");

    expect(result).toEqual({
      ok: false,
      error: { kind: "config_error", message: expect.any(String) },
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("normalizes a network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const result = await apiFetch("/health");

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe("network_error");
  });

  it("normalizes an abort into a timeout", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError")));

    const result = await apiFetch("/health");

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe("timeout");
  });

  it("parses a successful JSON response and propagates the correlation ID", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ status: "ok" }, { headers: { "X-Correlation-Id": "corr-1" } }),
        ),
    );

    const result = await apiFetch<{ status: string }>("/health");

    expect(result).toEqual({ ok: true, data: { status: "ok" }, correlationId: "corr-1" });
  });

  it("normalizes a non-JSON success body as malformed_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>not json</html>", { status: 200 })),
    );

    const result = await apiFetch("/health");

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe("malformed_response");
  });

  it("normalizes a documented API error envelope", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: {
              code: "dependency_unavailable",
              message: "A required dependency is not ready.",
              details: [],
              correlation_id: "corr-2",
            },
          },
          { status: 503 },
        ),
      ),
    );

    const result = await apiFetch("/api/v1/ready");

    expect(result).toEqual({
      ok: false,
      error: {
        kind: "api_error",
        message: "A required dependency is not ready.",
        code: "dependency_unavailable",
        correlationId: "corr-2",
        status: 503,
      },
    });
  });

  it("normalizes an undocumented error body as malformed_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ oops: true }, { status: 500 })),
    );

    const result = await apiFetch("/health");

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe("malformed_response");
  });
});
