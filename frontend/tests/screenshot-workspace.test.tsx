import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ScreenshotWorkspace } from "@/components/analysis/screenshot-workspace";

const ocr = { analysis_type: "ocr", extracted_text: "OCR text", usable_text: true, classification_performed: false, review_required: true, limitations: ["Review it."] };
const message = { analysis_type: "message", prediction: "ham", scores: { spam: .2, threshold: .5 }, interpretation: "Experimental output.", limitations: ["SMS baseline only."] };
const email = { analysis_type: "email", prediction: "Valid", classifier_outputs: { Valid: .7, Spam: .1, Phishing: .2 }, observed_indicators: ["Urgency language"], disagreement: true, disagreement_message: "The classifier predicted Valid, but indicators warrant verification.", verification_guidance: ["Verify independently."], limitations: ["Within-corpus only."], evaluation_scope: "within_corpus_only", generalization_status: "not_established" };
function response(body: unknown, status = 200): Response { return { ok: status < 400, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response; }
function select(name = "shot.png", size = 3, type = "image/png") { const file = new File([new Uint8Array(size)], name, { type }); fireEvent.change(screen.getByLabelText(/choose image/i), { target: { files: [file] } }); return file; }

describe("ScreenshotWorkspace", () => {
  beforeEach(() => { vi.stubGlobal("fetch", vi.fn()); vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:preview"), revokeObjectURL: vi.fn() }); });
  afterEach(() => vi.unstubAllGlobals());
  it("renders the five-stage, private review-first workflow", () => { render(<ScreenshotWorkspace/>); const stages = screen.getByRole("navigation", { name: /Screenshot analysis stages/i }); for (const label of ["01Upload", "02OCR", "03Review", "04Choose type", "05Result"]) expect(stages).toHaveTextContent(label); expect(screen.getByText("Upload a screenshot to begin OCR")).toBeInTheDocument(); expect(screen.getByText(/Browser → configured ScamLens API → Tesseract OCR on the backend/i)).toBeInTheDocument(); });
  it("accepts supported images and rejects unsupported or oversized files", () => { render(<ScreenshotWorkspace/>); select(); expect(screen.getByText("shot.png")).toBeInTheDocument(); select("bad.gif", 2, "image/gif"); expect(screen.getByRole("alert")).toHaveTextContent(/unsupported/i); select("large.png", 5 * 1024 * 1024 + 1); expect(screen.getByRole("alert")).toHaveTextContent(/too large/i); });
  it("extracts on explicit action, keeps text editable, and does not classify automatically", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(ocr)); vi.stubGlobal("fetch", fetchMock); render(<ScreenshotWorkspace/>); select();
    expect(fetchMock).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole("button", { name: /extract text/i })); expect(screen.getByText(/Extracting English text/i)).toBeInTheDocument();
    await screen.findByDisplayValue("OCR text"); expect(fetchMock).toHaveBeenCalledTimes(1); expect(screen.getByText(/No classification has run/i)).toBeInTheDocument(); expect(screen.getByRole("button", { name: /Analyze as Message/i })).toBeInTheDocument(); expect(screen.getByRole("button", { name: /Analyze as Email/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/editable extracted text/i), { target: { value: "Corrected reviewed text" } }); expect(screen.getByDisplayValue("Corrected reviewed text")).toBeInTheDocument();
  });
  it("uses the Message path with exact reviewed text and invalidates stale results on edits, rerun, and image change", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(ocr)).mockResolvedValueOnce(response(message)).mockResolvedValueOnce(response(ocr)); vi.stubGlobal("fetch", fetchMock); render(<ScreenshotWorkspace/>); select(); fireEvent.click(screen.getByRole("button", { name: /extract text/i })); await screen.findByDisplayValue("OCR text");
    fireEvent.change(screen.getByLabelText(/editable extracted text/i), { target: { value: "Corrected reviewed text" } }); fireEvent.click(screen.getByRole("button", { name: /Analyze as Message/i })); await screen.findByRole("heading", { name: /Ham/ });
    expect(screen.getByText("Analyzed as Message")).toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toEqual({ text: "Corrected reviewed text" });
    fireEvent.change(screen.getByLabelText(/editable extracted text/i), { target: { value: "Changed" } }); expect(screen.queryByRole("heading", { name: /Ham/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /run ocr again/i })); await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3)); expect(screen.queryByRole("heading", { name: /Ham/ })).not.toBeInTheDocument();
    select("new.png"); expect(screen.queryByLabelText(/editable extracted text/i)).not.toBeInTheDocument();
  });
  it("uses the Email path with reviewed text as body and no invented subject", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(response(ocr)).mockResolvedValueOnce(response(email)); vi.stubGlobal("fetch", fetchMock); render(<ScreenshotWorkspace/>); select(); fireEvent.click(screen.getByRole("button", { name: /extract text/i })); await screen.findByDisplayValue("OCR text"); fireEvent.change(screen.getByLabelText(/editable extracted text/i), { target: { value: "Exact reviewed email body" } }); fireEvent.click(screen.getByRole("button", { name: /Analyze as Email/i })); await screen.findByRole("heading", { name: "Valid" });
    expect(fetchMock.mock.calls[1][0]).toMatch(/\/api\/analyze\/email$/); expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toEqual({ subject: "", body: "Exact reviewed email body" }); expect(screen.getByText("Analyzed as Email")).toBeInTheDocument(); expect(screen.getByText(/within corpus only/i)).toBeInTheDocument(); expect(screen.getByText(/not established/i)).toBeInTheDocument(); expect(screen.getByText("Urgency language")).toBeInTheDocument();
  });
  it("clears a stale Message result when the user switches to Email analysis", async () => {
    let resolveEmail!: (value: Response) => void; const fetchMock = vi.fn().mockResolvedValueOnce(response(ocr)).mockResolvedValueOnce(response(message)).mockImplementationOnce(() => new Promise<Response>((done) => { resolveEmail = done; })); vi.stubGlobal("fetch", fetchMock); render(<ScreenshotWorkspace/>); select(); fireEvent.click(screen.getByRole("button", { name: /extract text/i })); await screen.findByDisplayValue("OCR text"); fireEvent.click(screen.getByRole("button", { name: /Analyze as Message/i })); await screen.findByRole("heading", { name: /Ham/ }); fireEvent.click(screen.getByRole("button", { name: /Analyze as Email/i })); expect(screen.queryByRole("heading", { name: /Ham/ })).not.toBeInTheDocument(); expect(screen.getAllByText(/Analyzing as Email/i).length).toBeGreaterThan(0); resolveEmail(response(email)); await screen.findByRole("heading", { name: "Valid" });
  });
  it("handles empty OCR, server errors, and prevents duplicate OCR submission", async () => {
    let resolve!: (value: Response) => void; const fetchMock = vi.fn(() => new Promise<Response>((done) => { resolve = done; })); vi.stubGlobal("fetch", fetchMock); render(<ScreenshotWorkspace/>); select(); const button = screen.getByRole("button", { name: /extract text/i }); fireEvent.click(button); fireEvent.click(button); expect(fetchMock).toHaveBeenCalledTimes(1); resolve(response({ ...ocr, extracted_text: "", usable_text: false })); await screen.findByText(/No usable text was extracted/i);
  });
  it("sanitizes an unavailable OCR service", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("private transport detail"))); render(<ScreenshotWorkspace/>); select(); fireEvent.click(screen.getByRole("button", { name: /extract text/i })); const alert = await screen.findByRole("alert"); expect(alert).toHaveTextContent(/OCR unavailable/i); expect(alert).toHaveTextContent(/ScamLens API/i); expect(alert).not.toHaveTextContent(/private transport detail/i);
  });
});
