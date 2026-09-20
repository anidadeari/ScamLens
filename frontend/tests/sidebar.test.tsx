import { render, screen } from "@testing-library/react";
import { usePathname } from "next/navigation";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Sidebar } from "@/components/sidebar";

vi.mock("next/navigation", () => ({ usePathname: vi.fn() }));

describe("sidebar navigation", () => {
  beforeEach(() => vi.mocked(usePathname).mockReturnValue("/email"));

  it("renders every workspace and marks the current route", () => {
    render(<Sidebar />);
    const overview = screen.getAllByRole("navigation", { name: "Overview navigation" })[0];
    const analysis = screen.getAllByRole("navigation", { name: "Analysis navigation" })[0];
    const transparency = screen.getAllByRole("navigation", { name: "Transparency navigation" })[0];
    expect(overview).toHaveTextContent("Overview");
    for (const label of ["Message", "Email", "Screenshot", "URL"]) expect(analysis).toHaveTextContent(label);
    expect(transparency).toHaveTextContent("Model Performance");
    expect(screen.getAllByRole("link", { name: "Email" })[0]).toHaveAttribute("aria-current", "page");
    expect(screen.getAllByRole("link", { name: "Message" })[0]).not.toHaveAttribute("aria-current");
    expect(screen.getByLabelText("Open navigation")).toBeInTheDocument();
  });
});
