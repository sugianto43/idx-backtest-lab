import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SiteNav } from "./SiteNav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/datasets",
}));

describe("SiteNav", () => {
  it("renders a navigation landmark with a link per route", () => {
    render(<SiteNav />);

    const nav = screen.getByRole("navigation", { name: "Primary" });
    expect(nav).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(6);
  });

  it("marks only the current route with aria-current", () => {
    render(<SiteNav />);

    const current = screen.getByRole("link", { name: "Datasets" });
    expect(current).toHaveAttribute("aria-current", "page");

    const other = screen.getByRole("link", { name: "Home" });
    expect(other).not.toHaveAttribute("aria-current");
  });
});
