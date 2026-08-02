import { apiFetch } from "./client";
import type { ApiResult, PaginatedResponse } from "./types";

export interface DatasetSummary {
  dataset_id: string;
  name: string;
  source_name: string;
  source_reference: string | null;
  license_reference: string | null;
  bar_interval: string;
  timezone: string;
  adjustment_policy: string;
  instrument_mapping_policy: string;
  coverage_start_date: string | null;
  coverage_end_date: string | null;
  validation_status: string;
  validation_summary: string | null;
  created_at_utc: string;
  row_count: number;
  warning_count: number;
}

export interface DatasetWarning {
  code: string;
  message: string;
  source_row_number: number | null;
  created_at_utc: string;
}

export interface DatasetDetailResponse extends DatasetSummary {
  warnings: DatasetWarning[];
}

export type DatasetListResponse = PaginatedResponse<DatasetSummary>;

export interface DatasetImportResponse {
  import_id: string;
  dataset_id: string | null;
  status: "valid" | "warning";
  row_count: number;
  accepted_row_count: number;
  warning_count: number;
  started_at_utc: string;
  finished_at_utc: string;
}

export function fetchDatasets(params: {
  limit: number;
  offset: number;
}): Promise<ApiResult<DatasetListResponse>> {
  return apiFetch<DatasetListResponse>(
    `/api/v1/datasets?limit=${params.limit}&offset=${params.offset}`,
  );
}

export function fetchDataset(datasetId: string): Promise<ApiResult<DatasetDetailResponse>> {
  return apiFetch<DatasetDetailResponse>(`/api/v1/datasets/${encodeURIComponent(datasetId)}`);
}

export interface ImportFromYahooFinanceFields {
  ticker: string;
  instrument_identifier?: string;
  start_date: string;
  end_date: string;
  name: string;
  instrument_mapping_policy: string;
  allow_reimport?: boolean;
}

export function importDatasetFromYahooFinance(
  fields: ImportFromYahooFinanceFields,
): Promise<ApiResult<DatasetImportResponse>> {
  return apiFetch<DatasetImportResponse>("/api/v1/datasets:import-from-yahoo-finance", {
    method: "POST",
    json: fields,
    timeoutMs: 30000,
  });
}
