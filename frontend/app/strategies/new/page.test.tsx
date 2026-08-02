import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import NewStrategyPage from "./page";
import { createStrategy } from "@/lib/api/strategies";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/strategies", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/strategies")>();
  return { ...actual, createStrategy: vi.fn() };
});

const mockedCreateStrategy = vi.mocked(createStrategy);

describe("NewStrategyPage", () => {
  it("defaults to the SMA crossover kind with pre-filled parameter values", () => {
    render(<NewStrategyPage />);

    expect(screen.getByLabelText("Strategy kind")).toHaveValue("sma_crossover");
    expect(screen.getByLabelText("Fast window (bars)")).toHaveValue("10");
    expect(screen.getByLabelText("Slow window (bars)")).toHaveValue("30");
  });

  it("blocks submission when the name is missing, without calling the API", () => {
    render(<NewStrategyPage />);

    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/name is required/i);
    expect(mockedCreateStrategy).not.toHaveBeenCalled();
  });

  it("rejects decimal window values client-side", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Strategy name"), { target: { value: "Test" } });
    fireEvent.change(screen.getByLabelText("Fast window (bars)"), { target: { value: "2.5" } });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/whole number/i);
    expect(mockedCreateStrategy).not.toHaveBeenCalled();
  });

  it("rejects fast_window >= slow_window client-side", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Strategy name"), { target: { value: "Test" } });
    fireEvent.change(screen.getByLabelText("Fast window (bars)"), { target: { value: "30" } });
    fireEvent.change(screen.getByLabelText("Slow window (bars)"), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/fast window must be smaller/i);
    expect(mockedCreateStrategy).not.toHaveBeenCalled();
  });

  it("shows the derived eligible-after-bars preview as read-only, not editable", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Slow window (bars)"), { target: { value: "7" } });

    expect(screen.getByText(/Eligible starting at bar 7/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/eligible/i)).not.toBeInTheDocument();
  });

  it("switching kind resets parameter fields to that kind's defaults", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Strategy kind"), {
      target: { value: "rsi_threshold" },
    });

    expect(screen.getByLabelText("RSI period (bars)")).toHaveValue("14");
    expect(screen.getByLabelText("Oversold threshold")).toHaveValue("30");
    expect(screen.getByLabelText("Overbought threshold")).toHaveValue("70");
  });

  it("submits the sma_crossover contract payload and routes to the returned immutable detail", async () => {
    mockedCreateStrategy.mockResolvedValue({
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

    render(<NewStrategyPage />);
    fireEvent.change(screen.getByLabelText("Strategy name"), {
      target: { value: "SMA crossover 2/3" },
    });
    fireEvent.change(screen.getByLabelText("Fast window (bars)"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Slow window (bars)"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/strategies/strat-1/versions/1"));
    expect(mockedCreateStrategy).toHaveBeenCalledWith({
      name: "SMA crossover 2/3",
      kind: "sma_crossover",
      parameters: { fast_window: 2, slow_window: 3 },
      eligibleAfterBars: 3,
    });
  });

  it("submits an rsi_threshold payload with the kind-specific parameter shape", async () => {
    mockedCreateStrategy.mockResolvedValue({
      ok: true,
      data: {
        strategy_id: "strat-2",
        version: 1,
        schema_version: 1,
        name: "RSI 14",
        kind: "rsi_threshold",
        parameters: {
          period: 14,
          oversold_threshold: 30,
          overbought_threshold: 70,
          price_field: "close",
        },
        signal_policy: { signal_time: "bar_close", eligible_after_bars: 15, long_only: true },
        checksum: "sha256:def",
        created_at_utc: "2026-01-01T00:00:00Z",
      },
    });

    render(<NewStrategyPage />);
    fireEvent.change(screen.getByLabelText("Strategy name"), { target: { value: "RSI 14" } });
    fireEvent.change(screen.getByLabelText("Strategy kind"), {
      target: { value: "rsi_threshold" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/strategies/strat-2/versions/1"));
    expect(mockedCreateStrategy).toHaveBeenCalledWith({
      name: "RSI 14",
      kind: "rsi_threshold",
      parameters: { period: 14, oversold_threshold: 30, overbought_threshold: 70 },
      eligibleAfterBars: 15,
    });
  });

  it("selecting the custom kind shows two condition blocks by default, each with its own indicator", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Strategy kind"), {
      target: { value: "multi_indicator_combo" },
    });

    expect(screen.getByText("Condition 1")).toBeInTheDocument();
    expect(screen.getByText("Condition 2")).toBeInTheDocument();
    expect(screen.getByLabelText("Indicator", { selector: "#condition-0-kind" })).toHaveValue(
      "sma_crossover",
    );
    expect(screen.getByLabelText("Indicator", { selector: "#condition-1-kind" })).toHaveValue(
      "rsi_threshold",
    );
  });

  it("blocks combo submission when two conditions use the same indicator", () => {
    mockedCreateStrategy.mockClear();
    render(<NewStrategyPage />);
    fireEvent.change(screen.getByLabelText("Strategy name"), { target: { value: "Combo" } });
    fireEvent.change(screen.getByLabelText("Strategy kind"), {
      target: { value: "multi_indicator_combo" },
    });
    fireEvent.change(screen.getByLabelText("Indicator", { selector: "#condition-1-kind" }), {
      target: { value: "sma_crossover" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/different indicator/i);
    expect(mockedCreateStrategy).not.toHaveBeenCalled();
  });

  it("adds and removes combo conditions within the 2-3 bound", () => {
    render(<NewStrategyPage />);
    fireEvent.change(screen.getByLabelText("Strategy kind"), {
      target: { value: "multi_indicator_combo" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Add condition" }));
    expect(screen.getByText("Condition 3")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add condition" })).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Remove condition" })[0]);
    expect(screen.queryByText("Condition 3")).not.toBeInTheDocument();
  });

  it("submits a multi_indicator_combo payload with each condition's kind and parameters", async () => {
    mockedCreateStrategy.mockResolvedValue({
      ok: true,
      data: {
        strategy_id: "strat-3",
        version: 1,
        schema_version: 1,
        name: "SMA + RSI combo",
        kind: "multi_indicator_combo",
        parameters: { conditions: [] },
        signal_policy: { signal_time: "bar_close", eligible_after_bars: 30, long_only: true },
        checksum: "sha256:ghi",
        created_at_utc: "2026-01-01T00:00:00Z",
      },
    });

    render(<NewStrategyPage />);
    fireEvent.change(screen.getByLabelText("Strategy name"), {
      target: { value: "SMA + RSI combo" },
    });
    fireEvent.change(screen.getByLabelText("Strategy kind"), {
      target: { value: "multi_indicator_combo" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/strategies/strat-3/versions/1"));
    expect(mockedCreateStrategy).toHaveBeenCalledWith({
      name: "SMA + RSI combo",
      kind: "multi_indicator_combo",
      parameters: {
        conditions: [
          { kind: "sma_crossover", parameters: { fast_window: 10, slow_window: 30 } },
          {
            kind: "rsi_threshold",
            parameters: { period: 14, oversold_threshold: 30, overbought_threshold: 70 },
          },
        ],
      },
      eligibleAfterBars: 30,
    });
  });

  it("preserves entered values and shows a safe server error on validation failure", async () => {
    mockedCreateStrategy.mockResolvedValue({
      ok: false,
      error: {
        kind: "api_error",
        code: "validation_error",
        message: "The strategy specification is invalid.",
        correlationId: "corr-1",
      },
    });

    render(<NewStrategyPage />);
    fireEvent.change(screen.getByLabelText("Strategy name"), {
      target: { value: "SMA crossover 2/3" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByDisplayValue("SMA crossover 2/3")).toBeInTheDocument();
  });
});
