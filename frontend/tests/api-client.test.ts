import { afterEach, describe, expect, it, vi } from "vitest";
import { analyzeEmail, analyzeMessage, analyzeUrl, API_TIMEOUT_MS, ApiClientError, extractScreenshotText, getPerformance } from "@/lib/api";

const messageResponse = {
  analysis_type: "message", prediction: "spam",
  scores: { spam: 0.8, threshold: 0.4 },
  interpretation: "Experimental output.", limitations: ["Limited task."],
};
const emailResponse = {
  analysis_type: "email", prediction: "Spam",
  classifier_outputs: { Valid: 0.1, Spam: 0.8, Phishing: 0.1 },
  observed_indicators: [], disagreement: false, disagreement_message: null,
  verification_guidance: ["Verify independently."], limitations: ["Limited task."],
  evaluation_scope: "within_corpus_only", generalization_status: "not_established",
};
const performanceResponse = {
  source: "stored_artifacts", experiments_are_directly_comparable: false,
  message: { experiment: "message", evaluation_scope: "held_out", accuracy: .9, macro_f1: .8, target_recall_label: "spam", target_recall: .7, limitations: ["Limited."] },
  email: { experiment: "email", evaluation_scope: "within_corpus_only", accuracy: .8, macro_f1: .7, target_recall_label: "Phishing", target_recall: .6, limitations: ["Limited."] },
  url: { experiment: "url", evaluation_scope: "temporal", accuracy: .7, macro_f1: .6, target_recall_label: "phish", target_recall: .5, limitations: ["Limited."] },
};

function response(body: unknown, status = 200): Response {
  return { ok: status >= 200 && status < 300, status, json: vi.fn().mockResolvedValue(body) } as unknown as Response;
}

describe("analysis API client", () => {
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

  it("uses the configured message endpoint and exact payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(messageResponse));
    vi.stubGlobal("fetch", fetchMock);
    await expect(analyzeMessage("Submitted text")).resolves.toEqual(messageResponse);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/api\/analyze\/message$/), expect.objectContaining({ method: "POST", body: JSON.stringify({ text: "Submitted text" }) }));
  });

  it("uses the configured email endpoint and exact payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(emailResponse));
    vi.stubGlobal("fetch", fetchMock);
    await expect(analyzeEmail("Subject", "Body")).resolves.toEqual(emailResponse);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/api\/analyze\/email$/), expect.objectContaining({ body: JSON.stringify({ subject: "Subject", body: "Body" }) }));
  });

  it("rejects malformed successful responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ analysis_type: "message", prediction: "ham" })));
    await expect(analyzeMessage("Text")).rejects.toMatchObject({ kind: "unexpected" });
  });

  it("returns safe validation details and classifies network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "Enter a message." }, 422)));
    await expect(analyzeMessage(" ")).rejects.toEqual(new ApiClientError("validation", "Enter a message."));
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("raw internal detail")));
    await expect(analyzeMessage("Text")).rejects.toMatchObject({ kind: "unavailable", message: expect.not.stringContaining("raw internal") });
  });

  it("uploads OCR multipart data only to the configured OCR endpoint", async () => {
    const body = { analysis_type: "ocr", extracted_text: "Review me", usable_text: true, classification_performed: false, review_required: true, limitations: ["Review it."] };
    const fetchMock = vi.fn().mockResolvedValue(response(body)); vi.stubGlobal("fetch", fetchMock);
    await expect(extractScreenshotText(new File(["image"], "shot.png", { type: "image/png" }))).resolves.toEqual(body);
    const [target, init] = fetchMock.mock.calls[0];
    expect(target).toMatch(/\/api\/ocr$/); expect(init.body).toBeInstanceOf(FormData); expect(init.headers).not.toHaveProperty("Content-Type");
  });

  it("submits a URL only as JSON data to the ScamLens endpoint", async () => {
    const body = { analysis_type: "url", prediction: "benign", classifier_outputs: { benign: .7, phish: .3 }, observed_indicators: [], disagreement: false, disagreement_message: null, verification_guidance: ["Verify independently."], limitations: ["String only."] };
    const fetchMock = vi.fn().mockResolvedValue(response(body)); vi.stubGlobal("fetch", fetchMock);
    const submitted = "https://non-routable.invalid/a";
    await expect(analyzeUrl(submitted)).resolves.toEqual(body);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/api\/analyze\/url$/), expect.objectContaining({ body: JSON.stringify({ url: submitted }) }));
    expect(fetchMock.mock.calls[0][0]).not.toBe(submitted);
  });

  it("gets performance from the exact configured endpoint without submitted content", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(performanceResponse)); vi.stubGlobal("fetch", fetchMock);
    await expect(getPerformance()).resolves.toEqual(performanceResponse);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/api\/performance$/), expect.objectContaining({ method: "GET", headers: { Accept: "application/json" } }));
    expect(fetchMock.mock.calls[0][1]).not.toHaveProperty("body");
  });

  it("rejects malformed performance responses", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ ...performanceResponse, experiments_are_directly_comparable: true })));
    await expect(getPerformance()).rejects.toMatchObject({ kind: "unexpected" });
  });

  it.each([
    ["message", () => analyzeMessage("Text"), API_TIMEOUT_MS.message],
    ["email", () => analyzeEmail("Subject", "Body"), API_TIMEOUT_MS.email],
    ["URL", () => analyzeUrl("https://example.invalid"), API_TIMEOUT_MS.url],
    ["performance", () => getPerformance(), API_TIMEOUT_MS.performance],
    ["OCR", () => extractScreenshotText(new File(["image"], "shot.png", { type: "image/png" })), API_TIMEOUT_MS.ocr],
  ])("aborts a stalled %s request at its centralized timeout", async (_name, invoke, timeout) => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_target: string, init: RequestInit) => new Promise((_resolve, reject) => {
      init.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")), { once: true });
    })));
    const rejection = expect(invoke()).rejects.toMatchObject({ kind: "unavailable", message: expect.stringMatching(/timed out/i) });
    await vi.advanceTimersByTimeAsync(timeout);
    await rejection;
  });
});
