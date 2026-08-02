import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import OptimizationsPage from "./page";
import { fetchOptimizations } from "@/lib/api/optimizations";

vi.mock("@/lib/api/optimizations", () => ({
  fetchOptimizations: vi.fn(),
}));

const mockedFetchOptimizations = vi.mocked(fetchOptimizations);

describe("OptimizationsPage", () => {
  it("renders a single heading, the research disclaimer, and a link to create", () => {
    mockedFetchOptimizations.mockReturnValue(new Promise(() => {}));

    render(<OptimizationsPage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText(/may be overfit/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /create a new optimization/i })).toHaveAttribute(
      "href",
      "/optimizations/new",
    );
  });

  it("shows an empty state when there are no optimizations", async () => {
    mockedFetchOptimizations.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0, limit: 20, offset: 0 },
    });

    render(<OptimizationsPage />);

    await waitFor(() =>
      expect(screen.getByText("No optimizations have been created yet.")).toBeInTheDocument(),
    );
  });

  it("renders optimization rows linked to their detail page", async () => {
    mockedFetchOptimizations.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            optimization_id: "opt-1",
            status: "completed",
            dataset_id: "ds-1",
            instrument_id: "instr-1",
            base_strategy_name: "SMA grid",
            objective_metric_key: "total_return",
            candidate_count: 4,
            rejected_count: 0,
            max_candidate_count: 50,
            failure_code: null,
            created_at_utc: "2026-01-01T00:00:00Z",
            started_at_utc: "2026-01-01T00:00:01Z",
            finished_at_utc: "2026-01-01T00:00:05Z",
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });

    render(<OptimizationsPage />);

    await waitFor(() => expect(screen.getByText("SMA grid")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "SMA grid" })).toHaveAttribute(
      "href",
      "/optimizations/opt-1",
    );
  });

  it("shows a safe error state when the API call fails", async () => {
    mockedFetchOptimizations.mockResolvedValue({
      ok: false,
      error: { kind: "network_error", message: "Could not reach the API." },
    });

    render(<OptimizationsPage />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
