"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ProvenanceList } from "@/components/data/ProvenanceList";
import { WarningsList } from "@/components/data/WarningsList";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { fetchDataset, type DatasetDetailResponse } from "@/lib/api/datasets";
import type { ApiError } from "@/lib/api/types";

type State =
  | { kind: "loading" }
  | { kind: "error"; error: ApiError }
  | { kind: "loaded"; data: DatasetDetailResponse };

export default function DatasetDetailPage() {
  const params = useParams<{ dataset_id: string }>();
  const datasetId = params.dataset_id;
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetchDataset(datasetId).then((result) => {
      if (cancelled) return;
      if (result.ok) {
        setState({ kind: "loaded", data: result.data });
      } else {
        setState({ kind: "error", error: result.error });
      }
    });

    return () => {
      cancelled = true;
    };
  }, [datasetId]);

  if (state.kind === "loading") {
    return (
      <>
        <h1>Dataset</h1>
        <LoadingState label="Loading dataset…" />
      </>
    );
  }

  if (state.kind === "error") {
    return (
      <>
        <h1>Dataset</h1>
        <ErrorState error={state.error} />
      </>
    );
  }

  const dataset = state.data;

  return (
    <>
      <h1>{dataset.name}</h1>
      <Disclaimer />
      <section aria-labelledby="provenance-heading">
        <h2 id="provenance-heading">Provenance</h2>
        <ProvenanceList
          items={[
            { label: "Dataset ID", value: dataset.dataset_id },
            { label: "Source", value: dataset.source_name },
            { label: "Source reference", value: dataset.source_reference },
            { label: "License reference", value: dataset.license_reference },
            { label: "Bar interval", value: dataset.bar_interval },
            { label: "Timezone", value: dataset.timezone },
            { label: "Adjustment policy", value: dataset.adjustment_policy },
            { label: "Instrument mapping policy", value: dataset.instrument_mapping_policy },
            {
              label: "Coverage",
              value: `${dataset.coverage_start_date ?? "?"} – ${dataset.coverage_end_date ?? "?"}`,
            },
            { label: "Validation status", value: dataset.validation_status },
            { label: "Validation summary", value: dataset.validation_summary },
            { label: "Row count", value: String(dataset.row_count) },
            { label: "Created", value: dataset.created_at_utc },
          ]}
        />
      </section>
      <section aria-labelledby="warnings-heading">
        <h2 id="warnings-heading">Warnings</h2>
        <WarningsList
          warnings={dataset.warnings.map((warning) => ({
            code: warning.code,
            message: warning.message,
            sourceRowNumber: warning.source_row_number,
          }))}
        />
      </section>
    </>
  );
}
