import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SystemStatusPage from "./page";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("SystemStatusPage", () => {
  it("renders a single page heading and a loading state before data arrives", () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));

    render(<SystemStatusPage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("status")).toHaveTextContent("Checking API connectivity");
  });

  it("shows an unavailable state when the API cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    render(<SystemStatusPage />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByText("The API is not reachable.")).toBeInTheDocument();
  });

  it("shows a warning state when the API is live but the database is not ready", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: "ok" }))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            error: {
              code: "dependency_unavailable",
              message: "A required dependency is not ready.",
              details: [],
              correlation_id: "corr-1",
            },
          },
          503,
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<SystemStatusPage />);

    await waitFor(() => expect(screen.getByText(/database is not ready yet/)).toBeInTheDocument());
  });

  it("shows a ready state when both liveness and readiness succeed", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ status: "ok" }))
      .mockResolvedValueOnce(
        jsonResponse({
          status: "ok",
          service: "idx-backtesting-lab-api",
          version: "0.1.0",
          database: "ready",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<SystemStatusPage />);

    await waitFor(() => expect(screen.getByText(/Ready\./)).toBeInTheDocument());
    expect(screen.getByText("0.1.0")).toBeInTheDocument();
  });
});
