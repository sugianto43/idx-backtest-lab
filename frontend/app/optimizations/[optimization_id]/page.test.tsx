import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import OptimizationDetailPage from "./page";
import {
  executeOptimization,
  fetchOptimization,
  fetchOptimizationCandidates,
} from "@/lib/api/optimizations";

vi.mock("next/navigation", () => ({
  useParams: () => ({ optimization_id: "opt-1" }),
}));

vi.mock("@/lib/api/optimizations", () => ({
  fetchOptimization: vi.fn(),
  fetchOptimizationCandidates: vi.fn(),
  executeOptimization: vi.fn(),
}));

const mockedFetchOptimization = vi.mocked(fetchOptimization);
const mockedFetchOptimizationCandidates = vi.mocked(fetchOptimizationCandidates);
const mockedExecuteOptimization = vi.mocked(executeOptimization);

const CREATED_OPTIMIZATION = {
  optimization_id: "opt-1",
  status: "created",
  dataset_id: "ds-1",
  instrument_id: "instr-1",
  base_strategy_name: "SMA grid",
  objective_metric_key: "total_return",
  candidate_count: 4,
  rejected_count: 1,
  max_candidate_count: 50,
  failure_code: null,
  created_at_utc: "2026-01-01T00:00:00Z",
  started_at_utc: null,
  finished_at_utc: null,
  schema_version: 1,
  checksum: "sha256:abc",
  fast_window_grid: [2, 3],
  slow_window_grid: [4, 5],
  train_start: "2026-01-01",
  train_end: "2026-01-10",
  validation_start: "2026-01-11",
  validation_end: "2026-01-20",
  holdout_start: "2026-01-21",
  holdout_end: "2026-01-30",
  tie_break_rule: "highest_objective_value",
  manifest: { optimization_id: "opt-1" },
  selected_candidate_id: null,
  selection_reason: null,
  selection_audit: null,
  selected_at_utc: null,
  holdout: {
    sealed: true,
    run_id: null,
    objective_status: null,
    objective_value: null,
    objective_reason: null,
  },
};

const EMPTY_CANDIDATES = { ok: true as const, data: { items: [], total: 0, limit: 20, offset: 0 } };

describe("OptimizationDetailPage", () => {
  it("shows the holdout as sealed and prohibits reading it before completion", async () => {
    mockedFetchOptimization.mockResolvedValue({ ok: true, data: CREATED_OPTIMIZATION });
    mockedFetchOptimizationCandidates.mockResolvedValue(EMPTY_CANDIDATES);

    render(<OptimizationDetailPage />);

    await waitFor(() => expect(screen.getByText(/Holdout is sealed/)).toBeInTheDocument());
    expect(screen.queryByText(/Holdout run ID/)).not.toBeInTheDocument();
  });

  it("shows the rejected-candidate warning distinctly, not hidden by default", async () => {
    mockedFetchOptimization.mockResolvedValue({ ok: true, data: CREATED_OPTIMIZATION });
    mockedFetchOptimizationCandidates.mockResolvedValue(EMPTY_CANDIDATES);

    render(<OptimizationDetailPage />);

    await waitFor(() =>
      expect(screen.getByText(/1 candidate pair were rejected/)).toBeInTheDocument(),
    );
  });

  it("executes the optimization and reveals holdout once completed", async () => {
    mockedFetchOptimization.mockResolvedValueOnce({ ok: true, data: CREATED_OPTIMIZATION });
    mockedFetchOptimizationCandidates.mockResolvedValue(EMPTY_CANDIDATES);
    mockedExecuteOptimization.mockResolvedValue({
      ok: true,
      data: {
        ...CREATED_OPTIMIZATION,
        status: "completed",
        selected_candidate_id: "cand-1",
        selection_reason: "highest total_return",
        holdout: {
          sealed: false,
          run_id: "run-holdout-1",
          objective_status: "available",
          objective_value: "0.10",
          objective_reason: null,
        },
      },
    });

    render(<OptimizationDetailPage />);
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Execute optimization" })).toBeInTheDocument(),
    );

    mockedFetchOptimization.mockResolvedValueOnce({
      ok: true,
      data: {
        ...CREATED_OPTIMIZATION,
        status: "completed",
        selected_candidate_id: "cand-1",
        selection_reason: "highest total_return",
        holdout: {
          sealed: false,
          run_id: "run-holdout-1",
          objective_status: "available",
          objective_value: "0.10",
          objective_reason: null,
        },
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "Execute optimization" }));

    await waitFor(() => expect(screen.getByText("run-holdout-1")).toBeInTheDocument());
    expect(screen.getByText("0.10")).toBeInTheDocument();
  });

  it("shows a safe not-found state for an unknown optimization", async () => {
    mockedFetchOptimization.mockResolvedValue({
      ok: false,
      error: { kind: "api_error", code: "not_found", message: "Not found." },
    });
    mockedFetchOptimizationCandidates.mockResolvedValue(EMPTY_CANDIDATES);

    render(<OptimizationDetailPage />);

    await waitFor(() =>
      expect(screen.getByText("This optimization does not exist.")).toBeInTheDocument(),
    );
  });
});
