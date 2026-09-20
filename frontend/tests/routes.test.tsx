import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Screenshot from "@/app/screenshot/page";
import Url from "@/app/url/page";
import Performance from "@/app/performance/page";

describe("application routes", () => {
  it.each([["Screenshot Analysis", Screenshot], ["URL Analysis", Url]])("renders the integrated %s route", (title, Component) => {
    render(<Component />);
    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /coming in the next integration milestone/i })).not.toBeInTheDocument();
  });
  it("renders the integrated Model Performance route", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    render(<Performance />);
    expect(screen.getByRole("heading", { name: "Model Performance" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /coming in the next integration milestone/i })).not.toBeInTheDocument();
  });
});
