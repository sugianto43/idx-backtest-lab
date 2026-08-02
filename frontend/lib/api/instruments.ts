import { apiFetch } from "./client";
import type { ApiResult } from "./types";

export interface DatasetInstrumentMapping {
  mapping_id: string;
  dataset_id: string;
  source_instrument_identifier: string;
  instrument_id: string;
  effective_from: string;
  effective_to: string | null;
  decision_source: string;
  status: string;
  created_at_utc: string;
}

export interface DatasetInstrumentMappingListResponse {
  items: DatasetInstrumentMapping[];
}

/** Instruments already mapped to this dataset — the only instrument IDs a run/optimization
 * against this dataset can legally reference. */
export function fetchDatasetInstrumentMappings(
  datasetId: string,
): Promise<ApiResult<DatasetInstrumentMappingListResponse>> {
  return apiFetch<DatasetInstrumentMappingListResponse>(
    `/api/v1/datasets/${encodeURIComponent(datasetId)}/instrument-mappings`,
  );
}
