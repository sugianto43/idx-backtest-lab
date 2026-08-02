"use client";

import { useEffect, useState } from "react";
import { ErrorState } from "@/components/status/ErrorState";
import { LoadingState } from "@/components/status/LoadingState";
import { UnavailableState } from "@/components/status/UnavailableState";
import { WarningState } from "@/components/status/WarningState";
import { fetchLiveness, fetchReadiness } from "@/lib/api/health";
import type { ApiError } from "@/lib/api/types";

type SystemStatus =
  | { kind: "loading" }
  | { kind: "api_unavailable"; error: ApiError }
  | { kind: "database_unavailable"; version: string; service: string }
  | { kind: "ready"; version: string; service: string }
  | { kind: "unexpected_error"; error: ApiError };

export default function SystemStatusPage() {
  const [status, setStatus] = useState<SystemStatus>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function check() {
      const liveness = await fetchLiveness();
      if (!liveness.ok) {
        if (!cancelled) setStatus({ kind: "api_unavailable", error: liveness.error });
        return;
      }

      const readiness = await fetchReadiness();
      if (cancelled) return;

      if (readiness.ok) {
        setStatus({
          kind: "ready",
          version: readiness.data.version,
          service: readiness.data.service,
        });
        return;
      }

      if (
        readiness.error.kind === "api_error" &&
        readiness.error.code === "dependency_unavailable"
      ) {
        setStatus({
          kind: "database_unavailable",
          version: "unknown",
          service: "idx-backtesting-lab-api",
        });
        return;
      }

      setStatus({ kind: "unexpected_error", error: readiness.error });
    }

    void check();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <h1>System status</h1>
      {status.kind === "loading" && <LoadingState label="Checking API connectivity…" />}
      {status.kind === "api_unavailable" && (
        <>
          <UnavailableState message="The API is not reachable." />
          <ErrorState error={status.error} />
        </>
      )}
      {status.kind === "database_unavailable" && (
        <WarningState message="The API is live, but its database is not ready yet." />
      )}
      {status.kind === "unexpected_error" && <ErrorState error={status.error} />}
      {status.kind === "ready" && (
        <p role="status">
          Ready. Service <strong>{status.service}</strong>, version{" "}
          <strong>{status.version}</strong>, database ready.
        </p>
      )}
    </>
  );
}
