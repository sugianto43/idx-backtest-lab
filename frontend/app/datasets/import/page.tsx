"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { importDatasetFromYahooFinance } from "@/lib/api/datasets";
import type { ApiError } from "@/lib/api/types";

interface FormState {
  ticker: string;
  instrumentIdentifier: string;
  name: string;
  startDate: string;
  endDate: string;
  instrumentMappingPolicy: string;
  allowReimport: boolean;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

const INITIAL_FORM: FormState = {
  ticker: "",
  instrumentIdentifier: "",
  name: "",
  startDate: "2015-01-01",
  endDate: today(),
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
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setSubmitError(null);

    if (!form.ticker.trim() || !form.name.trim()) {
      setClientError("Ticker and dataset name are required.");
      return;
    }
    if (form.startDate >= form.endDate) {
      setClientError("Start date must be before end date.");
      return;
    }

    setSubmitting(true);
    const result = await importDatasetFromYahooFinance({
      ticker: form.ticker.trim(),
      instrument_identifier: form.instrumentIdentifier.trim() || undefined,
      start_date: form.startDate,
      end_date: form.endDate,
      name: form.name,
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
        Fetches daily OHLCV bars directly from Yahoo Finance for the given ticker. Submitting this
        form creates a new, immutable dataset version — it never overwrites an existing one. See{" "}
        <a
          href="https://github.com/sugianto43/idx-backtest-lab/blob/main/docs/adr/ADR-011-remove-manual-csv-import.md"
          target="_blank"
          rel="noreferrer"
        >
          ADR-011
        </a>{" "}
        for the personal/non-commercial-use terms this import relies on.
      </p>

      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="ticker">Yahoo Finance ticker</label>
          <input
            id="ticker"
            value={form.ticker}
            onChange={(event) => setForm({ ...form, ticker: event.target.value })}
            placeholder="BBCA.JK"
            required
            aria-describedby="ticker-help"
          />
          <p id="ticker-help">
            Use the Yahoo Finance symbol, e.g. <code>BBCA.JK</code> for an IDX-listed stock.
          </p>
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
          <label htmlFor="instrument_identifier">Instrument identifier (optional)</label>
          <input
            id="instrument_identifier"
            value={form.instrumentIdentifier}
            onChange={(event) => setForm({ ...form, instrumentIdentifier: event.target.value })}
            aria-describedby="instrument_identifier-help"
          />
          <p id="instrument_identifier-help">
            Defaults to the ticker if left blank. Used to map bars to an instrument.
          </p>
        </div>

        <div>
          <label htmlFor="start_date">Start date</label>
          <input
            id="start_date"
            type="date"
            value={form.startDate}
            onChange={(event) => setForm({ ...form, startDate: event.target.value })}
            required
          />
        </div>

        <div>
          <label htmlFor="end_date">End date</label>
          <input
            id="end_date"
            type="date"
            value={form.endDate}
            onChange={(event) => setForm({ ...form, endDate: event.target.value })}
            required
          />
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
            Allow re-fetching the same range as a new dataset version
          </label>
        </div>

        {clientError ? <p role="alert">{clientError}</p> : null}

        <button type="submit" disabled={submitting}>
          {submitting ? "Fetching…" : "Fetch from Yahoo Finance"}
        </button>
      </form>

      {submitting && <LoadingState label="Fetching data from Yahoo Finance…" />}
      {submitError && (
        <>
          <ErrorState error={submitError} />
          {detailText(submitError.details) && <p>Details: {detailText(submitError.details)}</p>}
          {submitError.code === "conflict" && (
            <p>
              An identical range was already imported. Check the &quot;Allow re-fetching&quot; box
              above to create a new version anyway, or{" "}
              <Link href="/datasets">browse existing datasets</Link>.
            </p>
          )}
        </>
      )}
    </>
  );
}
