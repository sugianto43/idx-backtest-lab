import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import StrategiesPage from "./page";
import { fetchStrategies } from "@/lib/api/strategies";

vi.mock("@/lib/api/strategies", () => ({
  fetchStrategies: vi.fn(),
}));

const mockedFetchStrategies = vi.mocked(fetchStrategies);

describe("StrategiesPage", () => {
  it("renders a single heading and a link to the create route", () => {
    mockedFetchStrategies.mockReturnValue(new Promise(() => {}));

    render(<StrategiesPage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("link", { name: /create a new strategy/i })).toHaveAttribute(
      "href",
      "/strategies/new",
    );
  });

  it("shows an empty state when there are no strategies", async () => {
    mockedFetchStrategies.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0, limit: 20, offset: 0 },
    });

    render(<StrategiesPage />);

    await waitFor(() =>
      expect(screen.getByText("No strategies have been created yet.")).toBeInTheDocument(),
    );
  });

  it("never labels a strategy as profitable or active, only shows its specification", async () => {
    mockedFetchStrategies.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
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
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });

    render(<StrategiesPage />);

    await waitFor(() => expect(screen.getByText("SMA crossover 2/3")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "SMA crossover 2/3" })).toHaveAttribute(
      "href",
      "/strategies/strat-1/versions/1",
    );
    expect(screen.queryByText(/profitable/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/active/i)).not.toBeInTheDocument();
  });

  it("shows a safe error state when the API call fails", async () => {
    mockedFetchStrategies.mockResolvedValue({
      ok: false,
      error: { kind: "network_error", message: "Could not reach the API." },
    });

    render(<StrategiesPage />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
