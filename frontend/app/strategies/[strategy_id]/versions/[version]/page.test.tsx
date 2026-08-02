import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import StrategyVersionDetailPage from "./page";
import { fetchStrategyVersion } from "@/lib/api/strategies";

vi.mock("next/navigation", () => ({
  useParams: () => ({ strategy_id: "strat-1", version: "1" }),
}));

vi.mock("@/lib/api/strategies", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/strategies")>();
  return { ...actual, fetchStrategyVersion: vi.fn() };
});

const mockedFetchStrategyVersion = vi.mocked(fetchStrategyVersion);

describe("StrategyVersionDetailPage", () => {
  it("renders the immutable specification without editable controls", async () => {
    mockedFetchStrategyVersion.mockResolvedValue({
      ok: true,
      data: {
        strategy_id: "strat-1",
        version: 1,
        schema_version: 1,
        name: "SMA crossover 2/3",
        kind: "sma_crossover",
        parameters: { fast_window: 2, slow_window: 3, price_field: "close" },
        signal_policy: { signal_time: "bar_close", eligible_after_bars: 3, long_only: true },
        checksum: "sha256:abc",
        created_at_utc: "2026-01-01T00:00:00Z",
      },
    });

    render(<StrategyVersionDetailPage />);

    await waitFor(() => expect(screen.getByText("sha256:abc")).toBeInTheDocument());
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByText(/Eligible after bar: 3/)).toBeInTheDocument();
  });

  it("shows a safe not-found state for an unknown version", async () => {
    mockedFetchStrategyVersion.mockResolvedValue({
      ok: false,
      error: { kind: "api_error", code: "not_found", message: "Not found." },
    });

    render(<StrategyVersionDetailPage />);

    await waitFor(() =>
      expect(screen.getByText("This strategy version does not exist.")).toBeInTheDocument(),
    );
  });
});
