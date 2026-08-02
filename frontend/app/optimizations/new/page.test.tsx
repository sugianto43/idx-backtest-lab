import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import NewOptimizationPage from "./page";
import { createOptimization } from "@/lib/api/optimizations";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/optimizations", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api/optimizations")>("@/lib/api/optimizations");
  return { ...actual, createOptimization: vi.fn() };
});

const mockedCreateOptimization = vi.mocked(createOptimization);

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("Dataset ID"), { target: { value: "ds-1" } });
  fireEvent.change(screen.getByLabelText("Instrument ID"), { target: { value: "instr-1" } });
  fireEvent.change(screen.getByLabelText("Base strategy name"), {
    target: { value: "SMA grid" },
  });
  fireEvent.change(screen.getByLabelText("Fast SMA windows"), { target: { value: "2, 3" } });
  fireEvent.change(screen.getByLabelText("Slow SMA windows"), { target: { value: "4, 5" } });
  fireEvent.change(screen.getByLabelText("Train start"), { target: { value: "2026-01-01" } });
  fireEvent.change(screen.getByLabelText("Train end"), { target: { value: "2026-01-10" } });
  fireEvent.change(screen.getByLabelText("Validation start"), {
    target: { value: "2026-01-11" },
  });
  fireEvent.change(screen.getByLabelText("Validation end"), { target: { value: "2026-01-20" } });
  fireEvent.change(screen.getByLabelText("Holdout start"), { target: { value: "2026-01-21" } });
  fireEvent.change(screen.getByLabelText("Holdout end"), { target: { value: "2026-01-30" } });
}

describe("NewOptimizationPage", () => {
  it("shows a live, non-evaluating candidate-count preview from the declared grid", () => {
    render(<NewOptimizationPage />);

    fireEvent.change(screen.getByLabelText("Fast SMA windows"), { target: { value: "2, 6" } });
    fireEvent.change(screen.getByLabelText("Slow SMA windows"), { target: { value: "4" } });

    expect(screen.getByText(/Candidate count: 1 valid pair/)).toBeInTheDocument();
  });

  it("blocks submission when required identifiers are missing, without calling the API", () => {
    render(<NewOptimizationPage />);

    fireEvent.change(screen.getByLabelText("Fast SMA windows"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Slow SMA windows"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Create optimization" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/required/i);
    expect(mockedCreateOptimization).not.toHaveBeenCalled();
  });

  it("rejects decimal/non-integer window lists client-side", () => {
    render(<NewOptimizationPage />);

    fireEvent.change(screen.getByLabelText("Fast SMA windows"), { target: { value: "2.5" } });
    fireEvent.change(screen.getByLabelText("Slow SMA windows"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("button", { name: "Create optimization" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/positive whole numbers/i);
    expect(mockedCreateOptimization).not.toHaveBeenCalled();
  });

  it("rejects overlapping/reversed partitions client-side", () => {
    render(<NewOptimizationPage />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("Validation start"), {
      target: { value: "2026-01-05" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Create optimization" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/chronological/i);
    expect(mockedCreateOptimization).not.toHaveBeenCalled();
  });

  it("submits the contract payload and routes to the returned immutable detail", async () => {
    mockedCreateOptimization.mockResolvedValue({
      ok: true,
      data: { optimization_id: "opt-1" } as never,
    });

    render(<NewOptimizationPage />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Create optimization" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/optimizations/opt-1"));
    expect(mockedCreateOptimization).toHaveBeenCalledWith(
      expect.objectContaining({
        dataset_id: "ds-1",
        instrument_id: "instr-1",
        fast_windows: [2, 3],
        slow_windows: [4, 5],
        objective_metric_key: "total_return",
      }),
    );
  });

  it("preserves entered values and shows a safe server error on failure", async () => {
    mockedCreateOptimization.mockResolvedValue({
      ok: false,
      error: {
        kind: "api_error",
        code: "validation_error",
        message: "The optimization manifest is invalid.",
        correlationId: "corr-1",
      },
    });

    render(<NewOptimizationPage />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Create optimization" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByDisplayValue("ds-1")).toBeInTheDocument();
  });
});
