import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { EmailWorkspace } from "@/components/analysis/email-workspace";
import { analyzeEmail, type EmailAnalysis } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, analyzeEmail: vi.fn() };
});

const baseResult: EmailAnalysis = {
  analysis_type: "email", prediction: "Valid",
  classifier_outputs: { Valid: 0.682, Spam: 0.096, Phishing: 0.222 },
  observed_indicators: ["Urgency language", "Request to click or follow a link"],
  disagreement: true,
  disagreement_message: "The classifier predicted Valid, but the text contains indicators that warrant additional verification.",
  verification_guidance: ["Verify the request through an independently trusted website.", "Avoid email-provided links when in doubt."],
  limitations: ["Real-world generalization is not established."],
  evaluation_scope: "within_corpus_only", generalization_status: "not_established",
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  return { promise: new Promise<T>((done) => { resolve = done; }), resolve };
}

describe("Email workspace", () => {
  beforeEach(() => vi.mocked(analyzeEmail).mockReset());

  it("renders experimental scope and validates empty input", () => {
    render(<EmailWorkspace/>);
    expect(screen.getByRole("heading", { name: "Email Analysis" })).toBeInTheDocument();
    expect(screen.getByText("Within-corpus evaluation only")).toBeInTheDocument();
    expect(screen.getByText("Experimental")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter email content");
    expect(analyzeEmail).not.toHaveBeenCalled();
  });

  it("submits subject and body and renders three separate result layers", async () => {
    vi.mocked(analyzeEmail).mockResolvedValue(baseResult);
    render(<EmailWorkspace/>);
    fireEvent.change(screen.getByLabelText(/Subject/), { target: { value: "Urgent account message" } });
    fireEvent.change(screen.getByLabelText(/Body/), { target: { value: "Click the link" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    expect(analyzeEmail).toHaveBeenCalledWith("Urgent account message", "Click the link");
    await screen.findByRole("heading", { name: "Valid" });
    expect(screen.getByRole("heading", { name: "Classifier outputs" })).toBeInTheDocument();
    for (const value of ["0.682", "0.096", "0.222"]) expect(screen.getByText(value)).toBeInTheDocument();
    const observations = screen.getByRole("heading", { name: "Text-pattern observations" }).closest("section")!;
    expect(within(observations).getByText("Urgency language")).toBeInTheDocument();
    expect(within(observations).getByText("Request to click or follow a link")).toBeInTheDocument();
    const guidance = screen.getByRole("heading", { name: "What you can do next" }).closest("section")!;
    expect(within(guidance).getByText(/independently trusted website/i)).toBeInTheDocument();
    expect(screen.getByText("Model / evidence disagreement")).toBeInTheDocument();
    expect(screen.getByText(baseResult.disagreement_message!)).toBeInTheDocument();
    expect(screen.getByText(/observed indicators do not change/i)).toBeInTheDocument();
  });

  it("shows the supported no-indicator state without implying safety", async () => {
    vi.mocked(analyzeEmail).mockResolvedValue({ ...baseResult, observed_indicators: [], disagreement: false, disagreement_message: null });
    render(<EmailWorkspace/>);
    fireEvent.change(screen.getByLabelText(/Body/), { target: { value: "Ordinary text" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    await waitFor(() => expect(screen.getByText("No supported textual indicators were detected.")).toBeInTheDocument());
    expect(screen.getByText("This does not confirm that the email is safe.")).toBeInTheDocument();
    expect(screen.queryByText("Model / evidence disagreement")).not.toBeInTheDocument();
  });

  it("clears stale results when either input changes", async () => {
    vi.mocked(analyzeEmail).mockResolvedValue(baseResult);
    render(<EmailWorkspace/>);
    const subject = screen.getByLabelText(/Subject/);
    fireEvent.change(subject, { target: { value: "First" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    await screen.findByRole("heading", { name: "Valid" });
    fireEvent.change(subject, { target: { value: "Changed" } });
    expect(screen.queryByRole("heading", { name: "Valid" })).not.toBeInTheDocument();
    expect(screen.getByText("Enter email content to begin analysis")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Body/), { target: { value: "Body" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    await screen.findByRole("heading", { name: "Valid" });
    fireEvent.change(screen.getByLabelText(/Body/), { target: { value: "Changed body" } });
    expect(screen.queryByRole("heading", { name: "Valid" })).not.toBeInTheDocument();
  });

  it.each(["Subject", "Body"])("ignores an in-flight result after %s changes", async (field) => {
    const pending = deferred<EmailAnalysis>();
    vi.mocked(analyzeEmail).mockReturnValue(pending.promise);
    render(<EmailWorkspace/>);
    const input = screen.getByLabelText(new RegExp(field));
    fireEvent.change(input, { target: { value: "Email A" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    fireEvent.change(input, { target: { value: "Email B" } });
    pending.resolve(baseResult);
    await waitFor(() => expect(screen.getByText("Enter email content to begin analysis")).toBeInTheDocument());
    expect(screen.queryByRole("heading", { name: "Valid" })).not.toBeInTheDocument();
  });

  it("does not let an older response overwrite a newer result", async () => {
    const first = deferred<EmailAnalysis>(); const second = deferred<EmailAnalysis>();
    vi.mocked(analyzeEmail).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    render(<EmailWorkspace/>);
    const subject = screen.getByLabelText(/Subject/);
    fireEvent.change(subject, { target: { value: "Email A" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    fireEvent.change(subject, { target: { value: "Email B" } });
    fireEvent.click(screen.getByRole("button", { name: "Analyze email" }));
    second.resolve({ ...baseResult, prediction: "Spam", disagreement: false, disagreement_message: null });
    await screen.findByRole("heading", { name: "Spam" });
    first.resolve(baseResult);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Spam" })).toBeInTheDocument());
    expect(screen.queryByRole("heading", { name: "Valid" })).not.toBeInTheDocument();
  });

});
