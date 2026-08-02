import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DatasetsPage from "./page";
import { fetchDatasets } from "@/lib/api/datasets";

vi.mock("@/lib/api/datasets", () => ({
  fetchDatasets: vi.fn(),
}));

const mockedFetchDatasets = vi.mocked(fetchDatasets);

describe("DatasetsPage", () => {
  it("renders a single heading and a link to the import route", () => {
    mockedFetchDatasets.mockReturnValue(new Promise(() => {}));

    render(<DatasetsPage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("link", { name: /import a new dataset/i })).toHaveAttribute(
      "href",
      "/datasets/import",
    );
  });

  it("shows an empty state when there are no datasets", async () => {
    mockedFetchDatasets.mockResolvedValue({
      ok: true,
      data: { items: [], total: 0, limit: 20, offset: 0 },
    });

    render(<DatasetsPage />);

    await waitFor(() =>
      expect(screen.getByText("No datasets have been imported yet.")).toBeInTheDocument(),
    );
  });

  it("renders provenance columns including adjustment policy and warning count", async () => {
    mockedFetchDatasets.mockResolvedValue({
      ok: true,
      data: {
        items: [
          {
            dataset_id: "ds-1",
            name: "Sample dataset",
            source_name: "Manual export",
            source_reference: null,
            license_reference: "user_supplied_unknown",
            bar_interval: "1d",
            timezone: "UTC",
            adjustment_policy: "unknown",
            instrument_mapping_policy: "ticker_as_of_import",
            coverage_start_date: "2026-01-01",
            coverage_end_date: "2026-01-10",
            validation_status: "warning",
            validation_summary: null,
            created_at_utc: "2026-01-01T00:00:00Z",
            row_count: 10,
            warning_count: 1,
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });

    render(<DatasetsPage />);

    await waitFor(() => expect(screen.getByText("Sample dataset")).toBeInTheDocument());
    expect(screen.getByText("unknown")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sample dataset" })).toHaveAttribute(
      "href",
      "/datasets/ds-1",
    );
  });

  it("shows a safe error state when the API call fails", async () => {
    mockedFetchDatasets.mockResolvedValue({
      ok: false,
      error: { kind: "network_error", message: "Could not reach the API." },
    });

    render(<DatasetsPage />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
