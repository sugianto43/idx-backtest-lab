import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import NewOptimizationPage from "./page";
import { fetchDatasets } from "@/lib/api/datasets";
import { fetchDatasetInstrumentMappings } from "@/lib/api/instruments";
import { createOptimization } from "@/lib/api/optimizations";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/optimizations", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/optimizations")>();
  return { ...actual, createOptimization: vi.fn() };
});

vi.mock("@/lib/api/datasets", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/datasets")>();
  return { ...actual, fetchDatasets: vi.fn() };
});

vi.mock("@/lib/api/instruments", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/instruments")>();
  return { ...actual, fetchDatasetInstrumentMappings: vi.fn() };
});

const mockedCreateOptimization = vi.mocked(createOptimization);
const mockedFetchDatasets = vi.mocked(fetchDatasets);
const mockedFetchMappings = vi.mocked(fetchDatasetInstrumentMappings);

beforeEach(() => {
  mockedFetchDatasets.mockResolvedValue({
    ok: true,
    data: {
      items: [
        {
          dataset_id: "ds-1",
          name: "Sample dataset",
          source_name: "Yahoo Finance",
          source_reference: null,
          license_reference: null,
          bar_interval: "1d",
          timezone: "UTC",
          adjustment_policy: "split_adjusted",
          instrument_mapping_policy: "ticker_as_of_import",
          coverage_start_date: null,
          coverage_end_date: null,
          validation_status: "valid",
          validation_summary: null,
          created_at_utc: "2026-01-01T00:00:00Z",
          row_count: 10,
          warning_count: 0,
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    },
  });
  mockedFetchMappings.mockResolvedValue({
    ok: true,
    data: {
      items: [
        {
          mapping_id: "map-1",
          dataset_id: "ds-1",
          source_instrument_identifier: "BBCA",
          instrument_id: "instr-1",
          effective_from: "2026-01-01",
          effective_to: null,
          decision_source: "manual_review",
          status: "resolved",
          created_at_utc: "2026-01-01T00:00:00Z",
        },
      ],
    },
  });
});

async function fillRequiredFields() {
  fireEvent.change(await screen.findByLabelText("Dataset"), { target: { value: "ds-1" } });
  fireEvent.change(await screen.findByLabelText("Instrument"), {
    target: { value: "instr-1" },
  });
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

  it("loads instruments only after a dataset is selected", async () => {
    render(<NewOptimizationPage />);

    await screen.findByLabelText("Dataset");
    expect(screen.getByLabelText("Instrument")).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Dataset"), { target: { value: "ds-1" } });

    await waitFor(() => expect(screen.getByLabelText("Instrument")).not.toBeDisabled());
    expect(mockedFetchMappings).toHaveBeenCalledWith("ds-1");
  });

  it("rejects overlapping/reversed partitions client-side", async () => {
    render(<NewOptimizationPage />);
    await fillRequiredFields();
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
    await fillRequiredFields();
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
    await fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Create optimization" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByLabelText("Dataset")).toHaveValue("ds-1");
  });
});
