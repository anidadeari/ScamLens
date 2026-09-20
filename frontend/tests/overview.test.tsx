import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Overview from "@/app/page";

describe("overview", () => {
  it("renders the primary actions, evidence workflow, scope, and transparency path", () => {
    render(<Overview />);
    expect(screen.getByRole("heading", { name: /analyze suspicious content/i })).toBeInTheDocument();
    expect(screen.getByText(/results do not prove fraud/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^choose an analysis/i })).toHaveAttribute("href", "#workspaces");
    expect(screen.getByRole("link", { name: /see the workflow/i })).toHaveAttribute("href", "#workflow");
    expect(document.querySelectorAll("a.module-card")).toHaveLength(4);
    for (const name of ["Message", "Email", "Screenshot", "URL"]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
    expect(screen.getByText("OCR + review")).toBeInTheDocument();
    for (const name of ["Input", "ScamLens processing", "Observations", "Limitations", "Verification"]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
    expect(screen.getByText(/Analyzed as strings and never visited/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /view model performance/i })).toHaveAttribute("href", "/performance");
  });
});
