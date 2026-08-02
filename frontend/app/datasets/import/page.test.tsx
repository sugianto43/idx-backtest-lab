import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DatasetImportPage from "./page";
import { importDatasetFromYahooFinance } from "@/lib/api/datasets";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/datasets", () => ({
  importDatasetFromYahooFinance: vi.fn(),
}));

const mockedImport = vi.mocked(importDatasetFromYahooFinance);

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("Yahoo Finance ticker"), {
    target: { value: "BBCA.JK" },
  });
  fireEvent.change(screen.getByLabelText("Dataset name"), { target: { value: "Sample" } });
}

describe("DatasetImportPage", () => {
  it("blocks submission client-side when required fields are missing, without calling the API", () => {
    render(<DatasetImportPage />);

    fireEvent.click(screen.getByRole("button", { name: "Fetch from Yahoo Finance" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/ticker and dataset name/i);
    expect(mockedImport).not.toHaveBeenCalled();
  });

  it("blocks submission client-side when the start date is not before the end date", () => {
    render(<DatasetImportPage />);
    fillRequiredFields();
    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2026-01-01" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2025-01-01" } });

    fireEvent.click(screen.getByRole("button", { name: "Fetch from Yahoo Finance" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/start date must be before end date/i);
    expect(mockedImport).not.toHaveBeenCalled();
  });

  it("submits the ticker fields and routes to the new dataset on success", async () => {
    mockedImport.mockResolvedValue({
      ok: true,
      data: {
        import_id: "imp-1",
        dataset_id: "ds-1",
        status: "valid",
        row_count: 1,
        accepted_row_count: 1,
        warning_count: 0,
        started_at_utc: "2026-01-01T00:00:00Z",
        finished_at_utc: "2026-01-01T00:00:01Z",
      },
    });

    render(<DatasetImportPage />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Fetch from Yahoo Finance" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/datasets/ds-1"));
    expect(mockedImport).toHaveBeenCalledWith(
      expect.objectContaining({
        ticker: "BBCA.JK",
        name: "Sample",
        instrument_mapping_policy: "ticker_as_of_import",
      }),
    );
  });

  it("preserves entered values and shows a safe server error on conflict", async () => {
    mockedImport.mockResolvedValue({
      ok: false,
      error: {
        kind: "api_error",
        code: "conflict",
        message: "An identical dataset has already been imported.",
        correlationId: "corr-9",
        details: [{ existing_dataset_id: "ds-existing" }],
      },
    });

    render(<DatasetImportPage />);
    fillRequiredFields();
    fireEvent.click(screen.getByRole("button", { name: "Fetch from Yahoo Finance" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByDisplayValue("Sample")).toBeInTheDocument();
    expect(screen.getByText(/ds-existing/)).toBeInTheDocument();
  });
});
