import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MessageWorkspace } from "@/components/analysis/message-workspace";
import { EmailWorkspace } from "@/components/analysis/email-workspace";

function response(body: unknown, status: number): Response {
  return { ok: false, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response;
}

describe("workspace request failures", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("shows message API unavailability without internal details", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("private network detail")));
    render(<MessageWorkspace/>);
    fireEvent.change(screen.getByLabelText(/Message text/), { target: { value: "Text" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze message" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Analysis service unavailable");
    expect(alert).not.toHaveTextContent("private network detail");
  });

  it("shows safe message validation and server errors", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ detail: "Message input is invalid." }, 422))
      .mockResolvedValueOnce(response({ detail: "internal" }, 500));
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = render(<MessageWorkspace/>);
    fireEvent.change(screen.getByLabelText(/Message text/), { target: { value: "Text" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze message" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Check your message");
    expect(screen.getByRole("alert")).toHaveTextContent("Message input is invalid.");
    unmount();
    render(<MessageWorkspace/>);
    fireEvent.change(screen.getByLabelText(/Message text/), { target: { value: "Text" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze message" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Analysis unsuccessful");
    expect(screen.getByRole("alert")).not.toHaveTextContent("internal");
  });

  it("shows email API unavailability and validation errors", async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError("private network detail"))
      .mockResolvedValueOnce(response({ detail: "Email input is invalid." }, 422));
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = render(<EmailWorkspace/>);
    fireEvent.change(screen.getByLabelText(/Body/), { target: { value: "Text" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Analysis service unavailable");
    unmount();
    render(<EmailWorkspace/>);
    fireEvent.change(screen.getByLabelText(/Body/), { target: { value: "Text" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Check the email content");
    expect(screen.getByRole("alert")).toHaveTextContent("Email input is invalid.");
  });
});
