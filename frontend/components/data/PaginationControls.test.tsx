import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PaginationControls } from "./PaginationControls";

describe("PaginationControls", () => {
  it("disables Previous on the first page and Next on the last page", () => {
    render(
      <PaginationControls limit={20} offset={0} total={5} onPrevious={vi.fn()} onNext={vi.fn()} />,
    );

    expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  it("enables Next when more pages remain and calls the handler on click", () => {
    const onNext = vi.fn();
    render(
      <PaginationControls limit={20} offset={0} total={45} onPrevious={vi.fn()} onNext={onNext} />,
    );

    const next = screen.getByRole("button", { name: "Next" });
    expect(next).toBeEnabled();
    fireEvent.click(next);
    expect(onNext).toHaveBeenCalledOnce();
  });

  it("shows the current page and total", () => {
    render(
      <PaginationControls
        limit={20}
        offset={20}
        total={45}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
      />,
    );

    expect(screen.getByText("Page 2 of 3 (45 total)")).toBeInTheDocument();
  });
});
