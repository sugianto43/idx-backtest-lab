import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import NewStrategyPage from "./page";
import { createStrategy } from "@/lib/api/strategies";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/strategies", () => ({
  createStrategy: vi.fn(),
}));

const mockedCreateStrategy = vi.mocked(createStrategy);

function fillValidForm() {
  fireEvent.change(screen.getByLabelText("Strategy name"), {
    target: { value: "SMA crossover 2/3" },
  });
  fireEvent.change(screen.getByLabelText("Fast SMA window (bars)"), { target: { value: "2" } });
  fireEvent.change(screen.getByLabelText("Slow SMA window (bars)"), { target: { value: "3" } });
}

describe("NewStrategyPage", () => {
  it("blocks submission when the name is missing, without calling the API", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Fast SMA window (bars)"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Slow SMA window (bars)"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/name is required/i);
    expect(mockedCreateStrategy).not.toHaveBeenCalled();
  });

  it("rejects decimal and non-integer window values client-side", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Strategy name"), { target: { value: "Test" } });
    fireEvent.change(screen.getByLabelText("Fast SMA window (bars)"), {
      target: { value: "2.5" },
    });
    fireEvent.change(screen.getByLabelText("Slow SMA window (bars)"), { target: { value: "3" } });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/whole numbers/i);
    expect(mockedCreateStrategy).not.toHaveBeenCalled();
  });

  it("rejects scientific-notation and unsafe values client-side", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Strategy name"), { target: { value: "Test" } });
    fireEvent.change(screen.getByLabelText("Fast SMA window (bars)"), {
      target: { value: "1e3" },
    });
    fireEvent.change(screen.getByLabelText("Slow SMA window (bars)"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/whole numbers/i);
    expect(mockedCreateStrategy).not.toHaveBeenCalled();
  });

  it("rejects fast_window >= slow_window client-side", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Strategy name"), { target: { value: "Test" } });
    fireEvent.change(screen.getByLabelText("Fast SMA window (bars)"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Slow SMA window (bars)"), { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/fast window must be smaller/i);
    expect(mockedCreateStrategy).not.toHaveBeenCalled();
  });

  it("shows the derived eligible-after-bars value as read-only, not editable", () => {
    render(<NewStrategyPage />);

    fireEvent.change(screen.getByLabelText("Slow SMA window (bars)"), { target: { value: "7" } });

    expect(screen.getByText(/Eligible starting at bar 7/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/eligible/i)).not.toBeInTheDocument();
  });

  it("submits exactly the v1 contract payload and routes to the returned immutable detail", async () => {
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
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/strategies/strat-1/versions/1"));
    expect(mockedCreateStrategy).toHaveBeenCalledWith({
      name: "SMA crossover 2/3",
      fastWindow: 2,
      slowWindow: 3,
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
    fillValidForm();
    fireEvent.click(screen.getByRole("button", { name: "Create strategy" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByDisplayValue("SMA crossover 2/3")).toBeInTheDocument();
  });
});
