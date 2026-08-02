import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import RunDetailPage from "./page";
import { executeRun, fetchRun } from "@/lib/api/runs";
import {
  fetchReproducibilityManifest,
  fetchRunArtifacts,
  fetchRunEvents,
  fetchRunPortfolioSnapshots,
  fetchRunSummary,
} from "@/lib/api/run-artifacts";

vi.mock("next/navigation", () => ({
  useParams: () => ({ run_id: "run-1" }),
}));

vi.mock("@/lib/api/runs", () => ({
  fetchRun: vi.fn(),
  executeRun: vi.fn(),
}));

vi.mock("@/lib/api/run-artifacts", () => ({
  fetchRunSummary: vi.fn(),
  fetchRunArtifacts: vi.fn(),
  fetchReproducibilityManifest: vi.fn(),
  fetchRunEvents: vi.fn(),
  fetchRunPortfolioSnapshots: vi.fn(),
}));

const notFound = {
  ok: false as const,
  error: { kind: "api_error" as const, code: "not_found", message: "Not found." },
};

const baseRun = {
  ok: true as const,
  data: {
    run_id: "run-1",
    dataset_id: "ds-1",
    strategy_id: "strat-1",
    strategy_version: 1,
    schema_version: 1,
    status: "completed",
    manifest_checksum: "sha256:abc",
    manifest: { run_id: "run-1" },
    warning_count: 2,
    created_at_utc: "2026-01-01T00:00:00Z",
    final_equity: { status: "available" as const, value: "1000000.00", reason: null },
    total_return: { status: "available" as const, value: "0.05", reason: null },
  },
};

function mockAllNotFoundExceptRun() {
  vi.mocked(fetchRun).mockResolvedValue(baseRun);
  vi.mocked(fetchRunSummary).mockResolvedValue(notFound);
  vi.mocked(fetchRunArtifacts).mockResolvedValue(notFound);
  vi.mocked(fetchReproducibilityManifest).mockResolvedValue(notFound);
  vi.mocked(fetchRunEvents).mockResolvedValue(notFound);
  vi.mocked(fetchRunPortfolioSnapshots).mockResolvedValue(notFound);
}

describe("RunDetailPage", () => {
  it("shows an unavailable state for a run with no artifacts yet, distinct from a generic error", async () => {
    mockAllNotFoundExceptRun();

    render(<RunDetailPage />);

    await waitFor(() =>
      expect(
        screen.getByText("This run has not produced result artifacts yet. Execute it first."),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText(/2 warnings/)).toBeInTheDocument();
  });

  it("renders a not-found run as a safe unavailable state", async () => {
    vi.mocked(fetchRun).mockResolvedValue(notFound);
    vi.mocked(fetchRunSummary).mockResolvedValue(notFound);
    vi.mocked(fetchRunArtifacts).mockResolvedValue(notFound);
    vi.mocked(fetchReproducibilityManifest).mockResolvedValue(notFound);
    vi.mocked(fetchRunEvents).mockResolvedValue(notFound);
    vi.mocked(fetchRunPortfolioSnapshots).mockResolvedValue(notFound);

    render(<RunDetailPage />);

    await waitFor(() => expect(screen.getByText("This run does not exist.")).toBeInTheDocument());
  });

  it("renders metrics, provenance, events, and the full manifest when everything is available", async () => {
    vi.mocked(fetchRun).mockResolvedValue(baseRun);
    vi.mocked(fetchRunSummary).mockResolvedValue({
      ok: true,
      data: {
        run_id: "run-1",
        status: "completed",
        terminal_status: "completed",
        manifest_checksum: "sha256:abc",
        artifact_schema_version: 1,
        artifact_checksum: "sha256:def",
        event_count: 4,
        snapshot_count: 3,
        warning_count: 2,
        metrics: [
          {
            metric_key: "final_equity",
            status: "available",
            value: "1000000.00",
            reason: null,
            definition_version: 1,
          },
          {
            metric_key: "win_rate",
            status: "not_available",
            value: null,
            reason: "zero_trades",
            definition_version: 1,
          },
        ],
      },
    });
    vi.mocked(fetchRunArtifacts).mockResolvedValue({
      ok: true,
      data: {
        bundle_id: "bundle-1",
        run_id: "run-1",
        artifact_schema_version: 1,
        checksum: "sha256:def",
        terminal_status: "completed",
        provenance: { engine_adapter_name: "backtrader" },
        event_count: 4,
        snapshot_count: 3,
        metric_count: 2,
        created_at_utc: "2026-01-01T00:00:00Z",
        sections: {},
      },
    });
    vi.mocked(fetchReproducibilityManifest).mockResolvedValue(notFound);
    vi.mocked(fetchRunEvents).mockResolvedValue({
      ok: true,
      data: {
        type: "fill",
        items: [{ order_id: "o-1", price: "100.00" }],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });
    vi.mocked(fetchRunPortfolioSnapshots).mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            sequence: 0,
            timestamp_utc: "2026-01-01T00:00:00Z",
            cash: "1000.00",
            holdings_value: "0.00",
            total_equity: "1000.00",
            currency: "IDR",
            status: "valid",
            reason: null,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });

    render(<RunDetailPage />);

    await waitFor(() => expect(screen.getByText("win_rate")).toBeInTheDocument());
    expect(screen.getByText(/zero_trades/)).toBeInTheDocument();
    expect(screen.getByText("backtrader", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/"run_id": "run-1"/)).toBeInTheDocument();
  });

  it("shows an Execute run control only while status is created, and triggers execution", async () => {
    const createdRun = {
      ok: true as const,
      data: { ...baseRun.data, status: "created" },
    };
    vi.mocked(fetchRun).mockResolvedValue(createdRun);
    vi.mocked(fetchRunSummary).mockResolvedValue(notFound);
    vi.mocked(fetchRunArtifacts).mockResolvedValue(notFound);
    vi.mocked(fetchReproducibilityManifest).mockResolvedValue(notFound);
    vi.mocked(fetchRunEvents).mockResolvedValue(notFound);
    vi.mocked(fetchRunPortfolioSnapshots).mockResolvedValue(notFound);
    vi.mocked(executeRun).mockResolvedValue({
      ok: true,
      data: {
        run_id: "run-1",
        status: "completed",
        terminal_status: "completed",
        failure_code: null,
        order_count: 0,
        fill_count: 0,
        position_count: 0,
        cash_event_count: 0,
        warning_count: 0,
        note: "",
      },
    });

    render(<RunDetailPage />);

    const button = await screen.findByRole("button", { name: "Execute run" });
    fireEvent.click(button);

    await waitFor(() => expect(executeRun).toHaveBeenCalledWith("run-1"));
  });

  it("does not show an Execute run control once the run is completed", async () => {
    mockAllNotFoundExceptRun();

    render(<RunDetailPage />);

    await waitFor(() => expect(screen.getByText("Status")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Execute run" })).not.toBeInTheDocument();
  });
});
