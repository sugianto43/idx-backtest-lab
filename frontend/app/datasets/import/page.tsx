"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { importDataset } from "@/lib/api/datasets";
import type { ApiError } from "@/lib/api/types";

const MAX_FILE_BYTES = 10 * 1024 * 1024;

interface FormState {
  name: string;
  sourceName: string;
  sourceReference: string;
  licenseReference: string;
  barInterval: string;
  timezone: string;
  adjustmentPolicy: string;
  instrumentMappingPolicy: string;
  allowReimport: boolean;
}

const INITIAL_FORM: FormState = {
  name: "",
  sourceName: "",
  sourceReference: "",
  licenseReference: "",
  barInterval: "1d",
  timezone: "UTC",
  adjustmentPolicy: "raw",
  instrumentMappingPolicy: "ticker_as_of_import",
  allowReimport: false,
};

function detailText(details: unknown[] | undefined): string | null {
  if (!details || details.length === 0) return null;
  return details
    .map((detail) =>
      typeof detail === "object" && detail !== null ? JSON.stringify(detail) : String(detail),
    )
    .join("; ");
}

export default function DatasetImportPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [file, setFile] = useState<File | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setSubmitError(null);

    if (!file) {
      setClientError("Select a CSV file to import.");
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setClientError("This file is larger than the 10 MB limit the server enforces.");
      return;
    }
    if (!form.name.trim() || !form.sourceName.trim() || !form.licenseReference.trim()) {
      setClientError("Name, source name, and license reference are required.");
      return;
    }

    setSubmitting(true);
    const result = await importDataset({
      file,
      name: form.name,
      source_name: form.sourceName,
      source_reference: form.sourceReference || undefined,
      license_reference: form.licenseReference,
      bar_interval: form.barInterval,
      timezone: form.timezone,
      adjustment_policy: form.adjustmentPolicy,
      instrument_mapping_policy: form.instrumentMappingPolicy,
      allow_reimport: form.allowReimport,
    });
    setSubmitting(false);

    if (!result.ok) {
      setSubmitError(result.error);
      return;
    }
    if (result.data.dataset_id) {
      router.push(`/datasets/${result.data.dataset_id}`);
    }
  }

  return (
    <>
      <h1>Import a dataset</h1>
      <Disclaimer />
      <p>
        Submitting this form creates a new, immutable dataset version — it never overwrites an
        existing one. See the{" "}
        <a
          href="https://github.com/sugianto43/idx-backtest-lab/blob/main/docs/CSV_INGESTION_CONTRACT.md"
          target="_blank"
          rel="noreferrer"
        >
          CSV ingestion contract
        </a>{" "}
        for the exact file format. Client-side checks below are a convenience only — the server
        validates authoritatively.
      </p>

      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="file">CSV file (max 10 MB)</label>
          <input
            id="file"
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </div>

        <div>
          <label htmlFor="name">Dataset name</label>
          <input
            id="name"
            value={form.name}
            onChange={(event) => setForm({ ...form, name: event.target.value })}
            required
          />
        </div>

        <div>
          <label htmlFor="source_name">Source name</label>
          <input
            id="source_name"
            value={form.sourceName}
            onChange={(event) => setForm({ ...form, sourceName: event.target.value })}
            required
          />
          <p id="source_name-help">Human-readable legal/source label.</p>
        </div>

        <div>
          <label htmlFor="source_reference">Source reference (optional)</label>
          <input
            id="source_reference"
            value={form.sourceReference}
            onChange={(event) => setForm({ ...form, sourceReference: event.target.value })}
          />
          <p id="source_reference-help">Provider/export reference. Never include credentials.</p>
        </div>

        <div>
          <label htmlFor="license_reference">License reference</label>
          <input
            id="license_reference"
            value={form.licenseReference}
            onChange={(event) => setForm({ ...form, licenseReference: event.target.value })}
            required
            aria-describedby="license_reference-help"
          />
          <p id="license_reference-help">
            A URL/text reference to applicable terms, or the literal value{" "}
            <code>user_supplied_unknown</code>.
          </p>
        </div>

        <div>
          <label htmlFor="bar_interval">Bar interval</label>
          <input
            id="bar_interval"
            value={form.barInterval}
            onChange={(event) => setForm({ ...form, barInterval: event.target.value })}
            required
            aria-describedby="bar_interval-help"
          />
          <p id="bar_interval-help">Canonical interval, e.g. 1d, 1h, 5m.</p>
        </div>

        <div>
          <label htmlFor="timezone">Timezone</label>
          <input
            id="timezone"
            value={form.timezone}
            onChange={(event) => setForm({ ...form, timezone: event.target.value })}
            required
            aria-describedby="timezone-help"
          />
          <p id="timezone-help">IANA timezone for timestamps, or UTC.</p>
        </div>

        <div>
          <label htmlFor="adjustment_policy">Adjustment policy</label>
          <select
            id="adjustment_policy"
            value={form.adjustmentPolicy}
            onChange={(event) => setForm({ ...form, adjustmentPolicy: event.target.value })}
            aria-describedby="adjustment_policy-help"
          >
            <option value="raw">raw</option>
            <option value="split_adjusted">split_adjusted</option>
            <option value="total_return_adjusted">total_return_adjusted</option>
            <option value="unknown">unknown</option>
          </select>
          <p id="adjustment_policy-help">
            <code>unknown</code> imports with a prominent warning and cannot silently become another
            value later.
          </p>
        </div>

        <div>
          <label htmlFor="instrument_mapping_policy">Instrument mapping policy</label>
          <select
            id="instrument_mapping_policy"
            value={form.instrumentMappingPolicy}
            onChange={(event) => setForm({ ...form, instrumentMappingPolicy: event.target.value })}
          >
            <option value="ticker_as_of_import">ticker_as_of_import</option>
            <option value="provided_internal_id">provided_internal_id</option>
          </select>
        </div>

        <div>
          <label htmlFor="allow_reimport">
            <input
              id="allow_reimport"
              type="checkbox"
              checked={form.allowReimport}
              onChange={(event) => setForm({ ...form, allowReimport: event.target.checked })}
            />{" "}
            Allow re-importing identical file bytes as a new dataset version
          </label>
        </div>

        {clientError ? <p role="alert">{clientError}</p> : null}

        <button type="submit" disabled={submitting}>
          {submitting ? "Importing…" : "Import dataset"}
        </button>
      </form>

      {submitting && <LoadingState label="Importing dataset…" />}
      {submitError && (
        <>
          <ErrorState error={submitError} />
          {detailText(submitError.details) && <p>Details: {detailText(submitError.details)}</p>}
          {submitError.code === "conflict" && (
            <p>
              An identical file was already imported. Check the &quot;Allow re-importing&quot; box
              above to create a new version anyway, or{" "}
              <Link href="/datasets">browse existing datasets</Link>.
            </p>
          )}
        </>
      )}
    </>
  );
}
