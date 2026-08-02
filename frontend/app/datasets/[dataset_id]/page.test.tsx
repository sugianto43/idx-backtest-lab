import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import DatasetDetailPage from "./page";
import { fetchDataset } from "@/lib/api/datasets";

vi.mock("next/navigation", () => ({
  useParams: () => ({ dataset_id: "ds-1" }),
}));

vi.mock("@/lib/api/datasets", () => ({
  fetchDataset: vi.fn(),
}));

const mockedFetchDataset = vi.mocked(fetchDataset);

describe("DatasetDetailPage", () => {
  it("renders immutable provenance and always-visible warnings", async () => {
    mockedFetchDataset.mockResolvedValue({
      ok: true,
      data: {
        dataset_id: "ds-1",
        name: "Sample dataset",
        source_name: "Manual export",
        source_reference: "export-42",
        license_reference: "user_supplied_unknown",
        bar_interval: "1d",
        timezone: "UTC",
        adjustment_policy: "unknown",
        instrument_mapping_policy: "ticker_as_of_import",
        coverage_start_date: "2026-01-01",
        coverage_end_date: "2026-01-10",
        validation_status: "warning",
        validation_summary: "1 warning",
        created_at_utc: "2026-01-01T00:00:00Z",
        row_count: 10,
        warning_count: 1,
        warnings: [
          {
            code: "unknown_adjustment_policy",
            message: "Adjustment policy is unknown.",
            source_row_number: null,
            created_at_utc: "2026-01-01T00:00:00Z",
          },
        ],
      },
    });

    render(<DatasetDetailPage />);

    await waitFor(() => expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1));
    expect(screen.getByText("ds-1")).toBeInTheDocument();
    expect(screen.getByText("export-42")).toBeInTheDocument();
    expect(screen.getByText(/unknown_adjustment_policy/)).toBeInTheDocument();
  });

  it("shows a safe not-found state for an unknown dataset", async () => {
    mockedFetchDataset.mockResolvedValue({
      ok: false,
      error: {
        kind: "api_error",
        code: "not_found",
        message: "The requested resource was not found.",
      },
    });

    render(<DatasetDetailPage />);

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });
});
