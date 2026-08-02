import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DatasetImportPage from "./page";
import { importDataset } from "@/lib/api/datasets";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api/datasets", () => ({
  importDataset: vi.fn(),
}));

const mockedImportDataset = vi.mocked(importDataset);

function fillRequiredFields() {
  fireEvent.change(screen.getByLabelText("Dataset name"), { target: { value: "Sample" } });
  fireEvent.change(screen.getByLabelText("Source name"), { target: { value: "Manual export" } });
  fireEvent.change(screen.getByLabelText("License reference"), {
    target: { value: "user_supplied_unknown" },
  });
  const file = new File(
    ["timestamp,instrument_identifier,open,high,low,close,volume"],
    "prices.csv",
    {
      type: "text/csv",
    },
  );
  fireEvent.change(screen.getByLabelText(/CSV file/), { target: { files: [file] } });
}

describe("DatasetImportPage", () => {
  it("blocks submission client-side when no file is selected, without calling the API", () => {
    render(<DatasetImportPage />);

    fireEvent.click(screen.getByRole("button", { name: "Import dataset" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/select a csv file/i);
    expect(mockedImportDataset).not.toHaveBeenCalled();
  });

  it("blocks submission client-side when required text fields are missing, without calling the API", () => {
    render(<DatasetImportPage />);

    const file = new File(["timestamp"], "prices.csv", { type: "text/csv" });
    fireEvent.change(screen.getByLabelText(/CSV file/), { target: { files: [file] } });
    fireEvent.click(screen.getByRole("button", { name: "Import dataset" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/required/i);
    expect(mockedImportDataset).not.toHaveBeenCalled();
  });

  it("submits exactly the contract fields and routes to the new dataset on success", async () => {
    mockedImportDataset.mockResolvedValue({
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
    fireEvent.click(screen.getByRole("button", { name: "Import dataset" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/datasets/ds-1"));
    expect(mockedImportDataset).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Sample",
        source_name: "Manual export",
        license_reference: "user_supplied_unknown",
        bar_interval: "1d",
        timezone: "UTC",
        adjustment_policy: "raw",
        instrument_mapping_policy: "ticker_as_of_import",
      }),
    );
  });

  it("preserves entered values and shows a safe server error on conflict", async () => {
    mockedImportDataset.mockResolvedValue({
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
    fireEvent.click(screen.getByRole("button", { name: "Import dataset" }));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByDisplayValue("Sample")).toBeInTheDocument();
    expect(screen.getByText(/ds-existing/)).toBeInTheDocument();
  });
});
