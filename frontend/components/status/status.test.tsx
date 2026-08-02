import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingState } from "./LoadingState";
import { UnavailableState } from "./UnavailableState";
import { WarningState } from "./WarningState";

describe("status components", () => {
  it("LoadingState announces itself politely", () => {
    render(<LoadingState />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading");
  });

  it("EmptyState renders plain informative text", () => {
    render(<EmptyState message="No runs yet." />);
    expect(screen.getByText("No runs yet.")).toBeInTheDocument();
  });

  it("WarningState is announced but visually distinct from an error", () => {
    render(<WarningState message="Some rows were skipped." />);
    const warning = screen.getByRole("status");
    expect(warning).toHaveTextContent("Warning: Some rows were skipped.");
  });

  it("UnavailableState is a status region distinct from an error", () => {
    render(<UnavailableState message="This capability is not built yet." />);
    expect(screen.getByRole("status")).toHaveTextContent("This capability is not built yet.");
  });

  it("ErrorState is an alert with a safe message, code, and correlation ID", () => {
    render(
      <ErrorState
        error={{
          kind: "api_error",
          message: "A required dependency is not ready.",
          code: "dependency_unavailable",
          correlationId: "corr-123",
        }}
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("A required dependency is not ready.");
    expect(alert).toHaveTextContent("dependency_unavailable");
    expect(alert).toHaveTextContent("corr-123");
  });

  it("ErrorState never requires a code or correlation ID to render safely", () => {
    render(<ErrorState error={{ kind: "network_error", message: "Could not reach the API." }} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Could not reach the API.");
  });
});
