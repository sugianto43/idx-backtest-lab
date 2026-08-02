import type { ApiError } from "@/lib/api/types";

export function ErrorState({ error }: { error: ApiError }) {
  return (
    <div role="alert" className="error-state">
      <p>{error.message}</p>
      <dl>
        {error.code ? (
          <>
            <dt>Code</dt>
            <dd>{error.code}</dd>
          </>
        ) : null}
        {error.correlationId ? (
          <>
            <dt>Correlation ID</dt>
            <dd>{error.correlationId}</dd>
          </>
        ) : null}
      </dl>
    </div>
  );
}
