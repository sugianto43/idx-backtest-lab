import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DatasetsPage from "./page";

describe("DatasetsPage", () => {
  it("renders one heading, states its owning task, and offers no fake controls", () => {
    render(<DatasetsPage />);

    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText(/TASK-010/)).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });
});
