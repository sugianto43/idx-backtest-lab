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

export interface ImportDatasetFields {
  file: File;
  name: string;
  source_name: string;
  license_reference: string;
  bar_interval: string;
  timezone: string;
  adjustment_policy: string;
  instrument_mapping_policy: string;
  source_reference?: string;
  allow_reimport?: boolean;
}

/** Sends exactly the CSV_INGESTION_CONTRACT metadata fields plus the file. */
export function importDataset(
  fields: ImportDatasetFields,
): Promise<ApiResult<DatasetImportResponse>> {
  const body = new FormData();
  body.set("file", fields.file);
  body.set("name", fields.name);
  body.set("source_name", fields.source_name);
  body.set("license_reference", fields.license_reference);
  body.set("bar_interval", fields.bar_interval);
  body.set("timezone", fields.timezone);
  body.set("adjustment_policy", fields.adjustment_policy);
  body.set("instrument_mapping_policy", fields.instrument_mapping_policy);
  if (fields.source_reference) body.set("source_reference", fields.source_reference);
  if (fields.allow_reimport) body.set("allow_reimport", "true");

  return apiFetch<DatasetImportResponse>("/api/v1/datasets:import", {
    method: "POST",
    body,
    timeoutMs: 30000,
  });
}
