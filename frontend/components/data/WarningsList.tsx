import { WarningState } from "@/components/status/WarningState";

export interface WarningItem {
  code: string;
  message: string;
  sourceRowNumber?: number | null;
}

/**
 * Always renders the full warning list alongside its count — warnings must
 * never be reachable only through a collapsed-by-default control.
 */
export function WarningsList({ warnings }: { warnings: WarningItem[] }) {
  if (warnings.length === 0) {
    return <p>No warnings.</p>;
  }

  return (
    <div>
      <WarningState message={`${warnings.length} warning${warnings.length === 1 ? "" : "s"}.`} />
      <ul>
        {warnings.map((warning, index) => (
          <li key={`${warning.code}-${index}`}>
            <strong>{warning.code}</strong>: {warning.message}
            {warning.sourceRowNumber != null ? ` (row ${warning.sourceRowNumber})` : ""}
          </li>
        ))}
      </ul>
    </div>
  );
}
