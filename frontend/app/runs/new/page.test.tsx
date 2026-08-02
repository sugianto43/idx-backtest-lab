import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import NewRunPage from "./page";
import { fetchDatasets } from "@/lib/api/datasets";
import { fetchDatasetInstrumentMappings } from "@/lib/api/instruments";
import { createRun } from "@/lib/api/runs";
import { fetchStrategies } from "@/lib/api/strategies";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/runs", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/runs")>();
  return { ...actual, createRun: vi.fn() };
});

vi.mock("@/lib/api/strategies", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/strategies")>();
  return { ...actual, fetchStrategies: vi.fn() };
});

vi.mock("@/lib/api/datasets", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/datasets")>();
  return { ...actual, fetchDatasets: vi.fn() };
});

vi.mock("@/lib/api/instruments", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/instruments")>();
  return { ...actual, fetchDatasetInstrumentMappings: vi.fn() };
});

const mockedCreateRun = vi.mocked(createRun);
const mockedFetchStrategies = vi.mocked(fetchStrategies);
const mockedFetchDatasets = vi.mocked(fetchDatasets);
const mockedFetchMappings = vi.mocked(fetchDatasetInstrumentMappings);

function mockPickerData() {
  mockedFetchStrategies.mockResolvedValue({
    ok: true,
    data: {
      items: [
        {
          strategy_id: "strat-1",
          version: 1,
          schema_version: 1,
          name: "SMA crossover",
          kind: "sma_crossover",
          parameters: { fast_window: 10, slow_window: 30, price_field: "close" },
          signal_policy: { signal_time: "bar_close", eligible_after_bars: 30, long_only: true },
          checksum: "sha256:abc",
          created_at_utc: "2026-01-01T00:00:00Z",
        },
      ],
      total: 1,
      limit: 100,
      offset: 0,
    },
  });
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
}

async function fillRequiredFields() {
  fireEvent.change(await screen.findByLabelText("Strategy"), {
    target: { value: "strat-1::1" },
  });
  fireEvent.change(screen.getByLabelText("Dataset"), { target: { value: "ds-1" } });
  fireEvent.change(await screen.findByLabelText("Instrument"), {
    target: { value: "instr-1" },
  });
  fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-01-01" } });
  fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2026-01-10" } });
}

describe("NewRunPage", () => {
  it("blocks submission when required selections are missing, without calling the API", async () => {
    mockPickerData();
    render(<NewRunPage />);

    await screen.findByLabelText("Strategy");
    fireEvent.click(screen.getByRole("button", { name: "Create run" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/select a strategy/i);
    expect(mockedCreateRun).not.toHaveBeenCalled();
  });

  it("blocks submission when start date is after end date", async () => {
    mockPickerData();
    render(<NewRunPage />);
    await fillRequiredFields();
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-02-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Create run" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/start date must not be after/i);
    expect(mockedCreateRun).not.toHaveBeenCalled();
  });

  it("loads instruments only after a dataset is selected", async () => {
    mockPickerData();
    render(<NewRunPage />);

    await screen.findByLabelText("Strategy");
    expect(screen.getByLabelText("Instrument")).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Dataset"), { target: { value: "ds-1" } });

    await waitFor(() => expect(screen.getByLabelText("Instrument")).not.toBeDisabled());
    expect(mockedFetchMappings).toHaveBeenCalledWith("ds-1");
  });

  it("submits exactly the v1 contract payload and routes to the created run's detail page", async () => {
    mockPickerData();
    mockedCreateRun.mockResolvedValue({
      ok: true,
      data: { run_id: "run-1" } as never,
    });

    render(<NewRunPage />);
    await fillRequiredFields();
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
    mockPickerData();
    mockedCreateRun.mockResolvedValue({
      ok: false,
      error: {
        kind: "api_error",
        code: "not_found",
        message: "The requested resource was not found.",
      },
    });

    render(<NewRunPage />);
    await fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Create run" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByLabelText("Strategy")).toHaveValue("strat-1::1");
  });
});
