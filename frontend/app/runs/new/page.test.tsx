import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import NewRunPage from "./page";
import { createRun } from "@/lib/api/runs";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/runs", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/runs")>("@/lib/api/runs");
  return { ...actual, createRun: vi.fn() };
});

const mockedCreateRun = vi.mocked(createRun);

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("Strategy ID"), { target: { value: "strat-1" } });
  fireEvent.change(screen.getByLabelText("Dataset ID"), { target: { value: "ds-1" } });
  fireEvent.change(screen.getByLabelText("Instrument ID"), { target: { value: "instr-1" } });
  fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-01-01" } });
  fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2026-01-10" } });
}

describe("NewRunPage", () => {
  it("blocks submission when required identifiers are missing, without calling the API", () => {
    render(<NewRunPage />);

    fireEvent.click(screen.getByRole("button", { name: "Create run" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/required/i);
    expect(mockedCreateRun).not.toHaveBeenCalled();
  });

  it("blocks submission when start date is after end date", () => {
    render(<NewRunPage />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-02-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Create run" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/start date must not be after/i);
    expect(mockedCreateRun).not.toHaveBeenCalled();
  });

  it("submits exactly the v1 contract payload and routes to the created run's detail page", async () => {
    mockedCreateRun.mockResolvedValue({
      ok: true,
      data: { run_id: "run-1" } as never,
    });

    render(<NewRunPage />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Create run" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/runs/run-1"));
    expect(mockedCreateRun).toHaveBeenCalledWith(
      expect.objectContaining({
        strategy_id: "strat-1",
        strategy_version: 1,
        dataset_id: "ds-1",
        instrument_ids: ["instr-1"],
        start_date: "2026-01-01",
        end_date: "2026-01-10",
      }),
    );
  });

  it("preserves entered values and shows a safe server error on failure", async () => {
    mockedCreateRun.mockResolvedValue({
      ok: false,
      error: {
        kind: "api_error",
        code: "not_found",
        message: "The requested resource was not found.",
      },
    });

    render(<NewRunPage />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Create run" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByDisplayValue("strat-1")).toBeInTheDocument();
  });
});
