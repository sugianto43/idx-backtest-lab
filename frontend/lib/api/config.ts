export type ApiBaseUrlConfig = { ok: true; baseUrl: string } | { ok: false; reason: string };

/**
 * The API base URL is intentionally never guessed or defaulted to a
 * hard-coded development hostname: missing/invalid configuration must
 * surface as an explicit, safe UI state instead.
 */
export function resolveApiBaseUrl(): ApiBaseUrlConfig {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL;

  if (!raw || raw.trim() === "") {
    return {
      ok: false,
      reason: "NEXT_PUBLIC_API_BASE_URL is not configured.",
    };
  }

  try {
    const parsed = new URL(raw);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return { ok: false, reason: "NEXT_PUBLIC_API_BASE_URL must use http or https." };
    }
    return { ok: true, baseUrl: raw.replace(/\/+$/, "") };
  } catch {
    return { ok: false, reason: "NEXT_PUBLIC_API_BASE_URL is not a valid URL." };
  }
}
