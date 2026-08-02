"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { Disclaimer } from "@/components/layout/Disclaimer";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { fetchDatasets, type DatasetSummary } from "@/lib/api/datasets";
import {
  fetchDatasetInstrumentMappings,
  type DatasetInstrumentMapping,
} from "@/lib/api/instruments";
import { createRun } from "@/lib/api/runs";
import { fetchStrategies, type StrategySpecResponse } from "@/lib/api/strategies";
import type { ApiError } from "@/lib/api/types";

const POSITIVE_INTEGER = /^[1-9]\d*$/;
const PICKER_PAGE_SIZE = 100;

interface FormState {
  strategyChoice: string;
  datasetId: string;
  instrumentId: string;
  startDate: string;
  endDate: string;
  capitalAmount: string;
  capitalCurrency: string;
  positionSizingFraction: string;
  quantityIncrement: string;
  moneyScale: string;
  annualizationBasis: string;
  riskFreeRate: string;
}

const INITIAL_FORM: FormState = {
  strategyChoice: "",
  datasetId: "",
  instrumentId: "",
  startDate: "",
  endDate: "",
  capitalAmount: "1000000.00",
  capitalCurrency: "IDR",
  positionSizingFraction: "0.50",
  quantityIncrement: "1",
  moneyScale: "2",
  annualizationBasis: "252",
  riskFreeRate: "0.00",
};

function strategyChoiceValue(strategy: StrategySpecResponse): string {
  return `${strategy.strategy_id}::${strategy.version}`;
}

export default function NewRunPage() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [strategies, setStrategies] = useState<StrategySpecResponse[] | null>(null);
  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null);
  const [mappings, setMappings] = useState<DatasetInstrumentMapping[] | null>(null);
  const [pickerError, setPickerError] = useState<ApiError | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchStrategies({ limit: PICKER_PAGE_SIZE, offset: 0 }),
      fetchDatasets({ limit: PICKER_PAGE_SIZE, offset: 0 }),
    ]).then(([strategiesResult, datasetsResult]) => {
      if (cancelled) return;
      if (strategiesResult.ok) setStrategies(strategiesResult.data.items);
      else setPickerError(strategiesResult.error);
      if (datasetsResult.ok) setDatasets(datasetsResult.data.items);
      else setPickerError(datasetsResult.error);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!form.datasetId) return;
    let cancelled = false;
    fetchDatasetInstrumentMappings(form.datasetId).then((result) => {
      if (cancelled) return;
      if (result.ok) setMappings(result.data.items);
      else setPickerError(result.error);
    });
    return () => {
      cancelled = true;
    };
  }, [form.datasetId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setSubmitError(null);

    const [strategyId, strategyVersionRaw] = form.strategyChoice.split("::");
    if (!strategyId || !POSITIVE_INTEGER.test(strategyVersionRaw ?? "")) {
      setClientError("Select a strategy.");
      return;
    }
    if (!form.datasetId) {
      setClientError("Select a dataset.");
      return;
    }
    if (!form.instrumentId) {
      setClientError("Select an instrument.");
      return;
    }
    if (!form.startDate || !form.endDate) {
      setClientError("Start and end dates are required.");
      return;
    }
    if (form.startDate > form.endDate) {
      setClientError("Start date must not be after end date.");
      return;
    }
    if (!POSITIVE_INTEGER.test(form.moneyScale.trim()) && form.moneyScale.trim() !== "0") {
      setClientError("Money scale must be a non-negative whole number.");
      return;
    }
    if (!POSITIVE_INTEGER.test(form.annualizationBasis.trim())) {
      setClientError("Annualization basis must be a positive whole number.");
      return;
    }

    setSubmitting(true);
    const result = await createRun({
      strategy_id: strategyId,
      strategy_version: Number(strategyVersionRaw),
      dataset_id: form.datasetId,
      instrument_ids: [form.instrumentId],
      start_date: form.startDate,
      end_date: form.endDate,
      capital_amount: form.capitalAmount,
      capital_currency: form.capitalCurrency,
      position_sizing_fraction: form.positionSizingFraction,
      quantity_increment: form.quantityIncrement,
      money_scale: Number(form.moneyScale),
      annualization_basis: Number(form.annualizationBasis),
      risk_free_rate: form.riskFreeRate,
    });
    setSubmitting(false);

    if (!result.ok) {
      setSubmitError(result.error);
      return;
    }
    router.push(`/runs/${result.data.run_id}`);
  }

  return (
    <>
      <h1>Create a run</h1>
      <Disclaimer />
      <p>
        This creates a new, immutable run manifest with status <code>created</code>. It does not
        execute automatically — execute it from the run&apos;s detail page once created. v1 supports
        exactly one instrument per run.
      </p>

      {pickerError && <ErrorState error={pickerError} />}

      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="strategy_choice">Strategy</label>
          <select
            id="strategy_choice"
            value={form.strategyChoice}
            onChange={(event) => setForm({ ...form, strategyChoice: event.target.value })}
            disabled={!strategies}
            required
            aria-describedby="strategy_choice-help"
          >
            <option value="" disabled>
              {strategies ? "Select a strategy…" : "Loading strategies…"}
            </option>
            {strategies?.map((strategy) => (
              <option key={strategyChoiceValue(strategy)} value={strategyChoiceValue(strategy)}>
                {strategy.name} (v{strategy.version})
              </option>
            ))}
          </select>
          <p id="strategy_choice-help">
            {strategies?.length === 0 ? (
              <>
                No strategies exist yet — <Link href="/strategies/new">create one</Link> first.
              </>
            ) : (
              "Create additional strategies from the strategies list."
            )}
          </p>
        </div>

        <div>
          <label htmlFor="dataset_id">Dataset</label>
          <select
            id="dataset_id"
            value={form.datasetId}
            onChange={(event) => {
              setForm({ ...form, datasetId: event.target.value, instrumentId: "" });
              setMappings(null);
            }}
            disabled={!datasets}
            required
            aria-describedby="dataset_id-help"
          >
            <option value="" disabled>
              {datasets ? "Select a dataset…" : "Loading datasets…"}
            </option>
            {datasets?.map((dataset) => (
              <option key={dataset.dataset_id} value={dataset.dataset_id}>
                {dataset.name}
              </option>
            ))}
          </select>
          <p id="dataset_id-help">
            {datasets?.length === 0 ? (
              <>
                No datasets exist yet — <Link href="/datasets/import">import one</Link> first.
              </>
            ) : (
              "Selecting a dataset loads its mapped instruments below."
            )}
          </p>
        </div>

        <div>
          <label htmlFor="instrument_id">Instrument</label>
          <select
            id="instrument_id"
            value={form.instrumentId}
            onChange={(event) => setForm({ ...form, instrumentId: event.target.value })}
            disabled={!form.datasetId || !mappings}
            required
            aria-describedby="instrument_id-help"
          >
            <option value="" disabled>
              {!form.datasetId
                ? "Select a dataset first…"
                : mappings
                  ? "Select an instrument…"
                  : "Loading instruments…"}
            </option>
            {mappings?.map((mapping) => (
              <option key={mapping.mapping_id} value={mapping.instrument_id}>
                {mapping.source_instrument_identifier}
              </option>
            ))}
          </select>
          <p id="instrument_id-help">
            {form.datasetId && mappings?.length === 0
              ? "No instruments are mapped to this dataset yet."
              : "Only instruments already mapped to the chosen dataset are shown."}
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
            aria-describedby="end_date-help"
          />
          <p id="end_date-help">Must be within the dataset&apos;s declared coverage range.</p>
        </div>

        <fieldset>
          <legend>Capital and execution assumptions</legend>
          <div>
            <label htmlFor="capital_amount">Capital amount</label>
            <input
              id="capital_amount"
              value={form.capitalAmount}
              onChange={(event) => setForm({ ...form, capitalAmount: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="capital_currency">Capital currency</label>
            <input
              id="capital_currency"
              value={form.capitalCurrency}
              onChange={(event) => setForm({ ...form, capitalCurrency: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="position_sizing_fraction">Position sizing fraction</label>
            <input
              id="position_sizing_fraction"
              value={form.positionSizingFraction}
              onChange={(event) => setForm({ ...form, positionSizingFraction: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="quantity_increment">Quantity increment</label>
            <input
              id="quantity_increment"
              value={form.quantityIncrement}
              onChange={(event) => setForm({ ...form, quantityIncrement: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="money_scale">Money scale (decimal places)</label>
            <input
              id="money_scale"
              inputMode="numeric"
              pattern="[0-9]*"
              value={form.moneyScale}
              onChange={(event) => setForm({ ...form, moneyScale: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="annualization_basis">Annualization basis (sessions/year)</label>
            <input
              id="annualization_basis"
              inputMode="numeric"
              pattern="[1-9][0-9]*"
              value={form.annualizationBasis}
              onChange={(event) => setForm({ ...form, annualizationBasis: event.target.value })}
              required
            />
          </div>
          <div>
            <label htmlFor="risk_free_rate">Risk-free rate</label>
            <input
              id="risk_free_rate"
              value={form.riskFreeRate}
              onChange={(event) => setForm({ ...form, riskFreeRate: event.target.value })}
              required
            />
          </div>
        </fieldset>

        {clientError ? <p role="alert">{clientError}</p> : null}

        <button type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create run"}
        </button>
      </form>

      {submitting && <LoadingState label="Creating run…" />}
      {submitError && <ErrorState error={submitError} />}
    </>
  );
}
