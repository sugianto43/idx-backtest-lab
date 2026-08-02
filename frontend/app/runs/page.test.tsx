import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import RunsPage from "./page";
import { fetchRuns } from "@/lib/api/runs";

vi.mock("@/lib/api/runs", () => ({
  fetchRuns: vi.fn(),
}));

const mockedFetchRuns = vi.mocked(fetchRuns);

describe("RunsPage", () => {
  it("shows an empty state when no runs exist", async () => {
    mockedFetchRuns.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0, limit: 20, offset: 0 },
    });

    render(<RunsPage />);

    await waitFor(() =>
      expect(screen.getByText("No backtest runs exist yet.")).toBeInTheDocument(),
    );
  });

  it("never renders an unavailable metric as zero and shows its reason", async () => {
    mockedFetchRuns.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            run_id: "run-1",
            dataset_id: "ds-1",
            strategy_id: "strat-1",
            strategy_version: 1,
            schema_version: 1,
            status: "created",
            manifest_checksum: "sha256:abc",
            manifest: {},
            warning_count: 0,
            created_at_utc: "2026-01-01T00:00:00Z",
            final_equity: { status: "not_available", value: null, reason: "run_not_yet_executed" },
            total_return: { status: "not_available", value: null, reason: "run_not_yet_executed" },
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });

    render(<RunsPage />);

    await waitFor(() => expect(screen.getByText("run-1")).toBeInTheDocument());
    const cells = screen.getAllByText(/Not available/);
    expect(cells).toHaveLength(2);
    expect(screen.getAllByText(/run_not_yet_executed/)).toHaveLength(2);
  });

  it("renders an available final equity value formatted for display", async () => {
    mockedFetchRuns.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            run_id: "run-2",
            dataset_id: "ds-1",
            strategy_id: "strat-1",
            strategy_version: 1,
            schema_version: 1,
            status: "completed",
            manifest_checksum: "sha256:abc",
            manifest: {},
            warning_count: 0,
            created_at_utc: "2026-01-01T00:00:00Z",
            final_equity: { status: "available", value: "1000000.00", reason: null },
            total_return: { status: "available", value: "0.05", reason: null },
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });

    render(<RunsPage />);

    await waitFor(() => expect(screen.getByText("1,000,000.00")).toBeInTheDocument());
    expect(screen.getByText("0.05")).toBeInTheDocument();
  });
});
