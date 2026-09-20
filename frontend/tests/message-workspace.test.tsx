import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MessageWorkspace } from "@/components/analysis/message-workspace";
import { analyzeMessage, type MessageAnalysis } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, analyzeMessage: vi.fn() };
});

const result: MessageAnalysis = {
  analysis_type: "message", prediction: "ham",
  scores: { spam: 0.18, threshold: 0.4 },
  interpretation: "Experimental SMS ham (non-spam) prediction; this does not confirm safety.",
  limitations: ["Not validated as a phishing, fraud, or safety detector.", "A ham prediction does not confirm that a message is safe."],
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  return { promise: new Promise<T>((done) => { resolve = done; }), resolve };
}

describe("Message workspace", () => {
  beforeEach(() => vi.mocked(analyzeMessage).mockReset());

  it("renders an accessible initial workspace and counter", () => {
    render(<MessageWorkspace/>);
    expect(screen.getByRole("heading", { name: "Message Analysis" })).toBeInTheDocument();
    expect(screen.getByLabelText(/Message text/)).toHaveAttribute("maxlength", "5000");
    expect(screen.getByText("0 / 5,000")).toBeInTheDocument();
    expect(screen.getByText("Paste a message to begin analysis")).toBeInTheDocument();
  });

  it("validates empty submission without calling the API", () => {
    render(<MessageWorkspace/>);
    fireEvent.click(screen.getByRole("button", { name: /analyze message/i }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a message");
    expect(screen.getByLabelText(/Message text/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText(/Message text/)).toHaveAttribute("aria-describedby", expect.stringContaining("message-error"));
    expect(analyzeMessage).not.toHaveBeenCalled();
  });

  it("submits explicitly, prevents duplicates while loading, and renders accurate output", async () => {
    let resolve!: (value: MessageAnalysis) => void;
    vi.mocked(analyzeMessage).mockReturnValue(new Promise((done) => { resolve = done; }));
    render(<MessageWorkspace/>);
    fireEvent.change(screen.getByLabelText(/Message text/), { target: { value: "Can you review this message?" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze message" }));
    expect(analyzeMessage).toHaveBeenCalledWith("Can you review this message?");
    expect(screen.getByRole("button", { name: /analyzing message/i })).toBeDisabled();
    expect(screen.getByText("Analyzing message")).toBeInTheDocument();
    resolve(result);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Ham (non-spam)" })).toBeInTheDocument());
    expect(screen.getByText("Spam model score")).toBeInTheDocument();
    expect(screen.getByText("0.180")).toBeInTheDocument();
    expect(screen.getByText("Classification threshold: 0.40")).toBeInTheDocument();
    expect(screen.getByText(/not a probability of fraud/i)).toBeInTheDocument();
    expect(screen.getByText("Keep this result in scope")).toBeInTheDocument();
    expect(screen.getByText(/does not confirm that the message is safe, authentic, or trustworthy/i)).toBeInTheDocument();
  });

  it("clears stale results when content changes", async () => {
    vi.mocked(analyzeMessage).mockResolvedValue(result);
    render(<MessageWorkspace/>);
    const input = screen.getByLabelText(/Message text/);
    fireEvent.change(input, { target: { value: "First text" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze message" }));
    await screen.findByRole("heading", { name: "Ham (non-spam)" });
    fireEvent.change(input, { target: { value: "Changed text" } });
    expect(screen.queryByRole("heading", { name: "Ham (non-spam)" })).not.toBeInTheDocument();
    expect(screen.getByText("Paste a message to begin analysis")).toBeInTheDocument();
  });

  it("ignores an in-flight result after the submitted text is edited", async () => {
    const first = deferred<MessageAnalysis>();
    vi.mocked(analyzeMessage).mockReturnValue(first.promise);
    render(<MessageWorkspace/>);
    const input = screen.getByLabelText(/Message text/);
    fireEvent.change(input, { target: { value: "Message A" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze message" }));
    fireEvent.change(input, { target: { value: "Message B" } });
    first.resolve(result);
    await waitFor(() => expect(screen.getByText("Paste a message to begin analysis")).toBeInTheDocument());
    expect(screen.queryByRole("heading", { name: "Ham (non-spam)" })).not.toBeInTheDocument();
  });

  it("does not let an older response overwrite a newer result", async () => {
    const first = deferred<MessageAnalysis>();
    const second = deferred<MessageAnalysis>();
    vi.mocked(analyzeMessage).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    render(<MessageWorkspace/>);
    const input = screen.getByLabelText(/Message text/);
    fireEvent.change(input, { target: { value: "Message A" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze message" }));
    fireEvent.change(input, { target: { value: "Message B" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze message" }));
    second.resolve({ ...result, prediction: "spam", scores: { spam: .9, threshold: .4 } });
    await screen.findByRole("heading", { name: "Spam" });
    expect(screen.getByText(/classifier evidence, not proof of fraud or malicious intent/i)).toBeInTheDocument();
    first.resolve(result);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Spam" })).toBeInTheDocument());
    expect(screen.queryByRole("heading", { name: "Ham (non-spam)" })).not.toBeInTheDocument();
  });

});
