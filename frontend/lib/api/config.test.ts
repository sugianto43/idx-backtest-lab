import { afterEach, describe, expect, it } from "vitest";
import { resolveApiBaseUrl } from "./config";

const ORIGINAL = process.env.NEXT_PUBLIC_API_BASE_URL;

afterEach(() => {
  if (ORIGINAL === undefined) {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  } else {
    process.env.NEXT_PUBLIC_API_BASE_URL = ORIGINAL;
  }
});

describe("resolveApiBaseUrl", () => {
  it("returns a safe error when unset", () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;

    const result = resolveApiBaseUrl();

    expect(result.ok).toBe(false);
  });

  it("returns a safe error for a non-URL value", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "not-a-url";

    const result = resolveApiBaseUrl();

    expect(result.ok).toBe(false);
  });

  it("rejects non-http(s) schemes", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "ftp://example.com";

    const result = resolveApiBaseUrl();

    expect(result.ok).toBe(false);
  });

  it("accepts a valid http URL and strips a trailing slash", () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/";

    const result = resolveApiBaseUrl();

    expect(result).toEqual({ ok: true, baseUrl: "http://localhost:8000" });
  });
});
