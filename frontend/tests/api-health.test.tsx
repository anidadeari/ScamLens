import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiHealth } from "@/components/api-health";

describe("API health status", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows loading and then genuinely available", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) }));
    render(<ApiHealth />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking system");
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("System ready"));
    expect(screen.getByRole("status")).toHaveTextContent("API connected");
  });

  it("keeps the interface usable when unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    render(<ApiHealth />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("API unavailable"));
    expect(screen.getByRole("status")).toHaveTextContent("Analysis service not connected");
  });
});
