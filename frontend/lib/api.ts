import { API_BASE_URL } from "@/lib/config";

export const MESSAGE_MAX_CHARACTERS = 5_000;
export const EMAIL_MAX_CHARACTERS = 100_000;
export const URL_MAX_CHARACTERS = 2_048;
export const SCREENSHOT_MAX_BYTES = 5 * 1024 * 1024;
export const SCREENSHOT_ACCEPT = ["image/png", "image/jpeg", "image/webp"] as const;

export const API_TIMEOUT_MS = {
  message: 15_000,
  email: 20_000,
  url: 15_000,
  ocr: 30_000,
  performance: 10_000,
} as const;

export type MessageAnalysis = {
  analysis_type: "message";
  prediction: "ham" | "spam";
  scores: { spam: number; threshold: number };
  interpretation: string;
  limitations: string[];
};

export type EmailAnalysis = {
  analysis_type: "email";
  prediction: "Valid" | "Spam" | "Phishing";
  classifier_outputs: { Valid: number; Spam: number; Phishing: number };
  observed_indicators: string[];
  disagreement: boolean;
  disagreement_message: string | null;
  verification_guidance: string[];
  limitations: string[];
  evaluation_scope: "within_corpus_only";
  generalization_status: "not_established";
};

export type OcrResult = {
  analysis_type: "ocr";
  extracted_text: string;
  usable_text: boolean;
  classification_performed: false;
  review_required: true;
  limitations: string[];
};

export type UrlAnalysis = {
  analysis_type: "url";
  prediction: "benign" | "phish";
  classifier_outputs: { benign: number; phish: number };
  observed_indicators: string[];
  disagreement: boolean;
  disagreement_message: string | null;
  verification_guidance: string[];
  limitations: string[];
};

export type ExperimentMetrics = {
  experiment: string;
  evaluation_scope: string;
  accuracy: number;
  macro_f1: number;
  target_recall_label: string;
  target_recall: number;
  limitations: string[];
};

export type PerformanceReport = {
  source: "stored_artifacts";
  experiments_are_directly_comparable: false;
  message: ExperimentMetrics;
  email: ExperimentMetrics;
  url: ExperimentMetrics;
};

export type ApiErrorKind = "validation" | "unavailable" | "server" | "unexpected";

export class ApiClientError extends Error {
  constructor(public readonly kind: ApiErrorKind, message: string) {
    super(message);
    this.name = "ApiClientError";
  }
}

export function normalizeApiError(value: unknown): ApiClientError {
  if (value instanceof ApiClientError) return value;
  if (isRecord(value) && ["validation", "unavailable", "server", "unexpected"].includes(String(value.kind)) && typeof value.message === "string") {
    return new ApiClientError(value.kind as ApiErrorKind, value.message);
  }
  return new ApiClientError("unexpected", "The analysis could not be completed.");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isMessageAnalysis(value: unknown): value is MessageAnalysis {
  if (!isRecord(value) || value.analysis_type !== "message") return false;
  if (value.prediction !== "ham" && value.prediction !== "spam") return false;
  if (!isRecord(value.scores)) return false;
  return isFiniteNumber(value.scores.spam) && isFiniteNumber(value.scores.threshold)
    && typeof value.interpretation === "string" && isStringArray(value.limitations);
}

function isEmailAnalysis(value: unknown): value is EmailAnalysis {
  if (!isRecord(value) || value.analysis_type !== "email") return false;
  if (!["Valid", "Spam", "Phishing"].includes(String(value.prediction))) return false;
  if (!isRecord(value.classifier_outputs)) return false;
  const outputs = value.classifier_outputs;
  const outputsValid = ["Valid", "Spam", "Phishing"].every((label) => isFiniteNumber(outputs[label]));
  return outputsValid && isStringArray(value.observed_indicators)
    && typeof value.disagreement === "boolean"
    && (value.disagreement_message === null || typeof value.disagreement_message === "string")
    && isStringArray(value.verification_guidance) && isStringArray(value.limitations)
    && value.evaluation_scope === "within_corpus_only"
    && value.generalization_status === "not_established";
}

function isOcrResult(value: unknown): value is OcrResult {
  return isRecord(value) && value.analysis_type === "ocr"
    && typeof value.extracted_text === "string" && typeof value.usable_text === "boolean"
    && value.classification_performed === false && value.review_required === true
    && isStringArray(value.limitations);
}

function isUrlAnalysis(value: unknown): value is UrlAnalysis {
  if (!isRecord(value) || value.analysis_type !== "url") return false;
  if (value.prediction !== "benign" && value.prediction !== "phish") return false;
  if (!isRecord(value.classifier_outputs)) return false;
  return isFiniteNumber(value.classifier_outputs.benign) && isFiniteNumber(value.classifier_outputs.phish)
    && isStringArray(value.observed_indicators) && typeof value.disagreement === "boolean"
    && (value.disagreement_message === null || typeof value.disagreement_message === "string")
    && isStringArray(value.verification_guidance) && isStringArray(value.limitations);
}

function isExperimentMetrics(value: unknown): value is ExperimentMetrics {
  return isRecord(value) && typeof value.experiment === "string" && typeof value.evaluation_scope === "string"
    && isFiniteNumber(value.accuracy) && isFiniteNumber(value.macro_f1)
    && typeof value.target_recall_label === "string" && isFiniteNumber(value.target_recall)
    && isStringArray(value.limitations);
}

function isPerformanceReport(value: unknown): value is PerformanceReport {
  return isRecord(value) && value.source === "stored_artifacts"
    && value.experiments_are_directly_comparable === false
    && isExperimentMetrics(value.message) && isExperimentMetrics(value.email) && isExperimentMetrics(value.url);
}

function validationMessage(body: unknown): string {
  if (!isRecord(body)) return "Check the submitted content and try again.";
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    const messages = body.detail.flatMap((item) => isRecord(item) && typeof item.message === "string" ? [item.message] : []);
    if (messages.length) return messages.join(" ");
  }
  return "Check the submitted content and try again.";
}

async function fetchWithTimeout(
  input: string,
  init: RequestInit,
  timeoutMs: number,
  timeoutMessage: string,
  externalSignal?: AbortSignal,
): Promise<Response> {
  const controller = new AbortController();
  let timedOut = false;
  const relayAbort = () => controller.abort();
  externalSignal?.addEventListener("abort", relayAbort, { once: true });
  if (externalSignal?.aborted) controller.abort();
  const timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
  try {
    return await fetch(input, { ...init, signal: controller.signal });
  } catch (error) {
    if (timedOut) throw new ApiClientError("unavailable", timeoutMessage);
    throw error;
  } finally {
    window.clearTimeout(timeout);
    externalSignal?.removeEventListener("abort", relayAbort);
  }
}

async function requestAnalysis<T>(path: string, payload: unknown, validate: (value: unknown) => value is T, timeoutMs: number): Promise<T> {
  let response: Response;
  try {
    response = await fetchWithTimeout(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payload),
    }, timeoutMs, "The analysis request timed out. Please try again.");
  } catch (error) {
    if (error instanceof ApiClientError) throw error;
    throw new ApiClientError("unavailable", "The ScamLens API is unavailable. Check the API connection and try again.");
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiClientError("unexpected", "The analysis service returned an unreadable response.");
  }
  if (!response.ok) {
    if (response.status === 422) throw new ApiClientError("validation", validationMessage(body));
    if (response.status === 429) throw new ApiClientError("unavailable", "Too many requests. Wait briefly before trying again.");
    if (response.status === 503) throw new ApiClientError("unavailable", "The requested analysis service is unavailable.");
    throw new ApiClientError("server", "The analysis could not be completed. Please try again.");
  }
  if (!validate(body)) throw new ApiClientError("unexpected", "The analysis service returned an unexpected response.");
  return body;
}

export function analyzeMessage(text: string): Promise<MessageAnalysis> {
  return requestAnalysis("/api/analyze/message", { text }, isMessageAnalysis, API_TIMEOUT_MS.message);
}

export function analyzeEmail(subject: string, body: string): Promise<EmailAnalysis> {
  return requestAnalysis("/api/analyze/email", { subject, body }, isEmailAnalysis, API_TIMEOUT_MS.email);
}

export function analyzeUrl(url: string): Promise<UrlAnalysis> {
  return requestAnalysis("/api/analyze/url", { url }, isUrlAnalysis, API_TIMEOUT_MS.url);
}

export async function extractScreenshotText(file: File, signal?: AbortSignal): Promise<OcrResult> {
  const form = new FormData();
  form.append("file", file, file.name);
  let response: Response;
  try {
    response = await fetchWithTimeout(`${API_BASE_URL}/api/ocr`, { method: "POST", headers: { Accept: "application/json" }, body: form }, API_TIMEOUT_MS.ocr, "OCR timed out. Try again with a smaller image.", signal);
  } catch (error) {
    if (error instanceof ApiClientError) throw error;
    if (isRecord(error) && error.name === "AbortError") throw new ApiClientError("unavailable", "OCR timed out. Try again with a smaller image.");
    throw new ApiClientError("unavailable", "The OCR service is unavailable. Check the ScamLens API and try again.");
  }
  let body: unknown;
  try { body = await response.json(); }
  catch { throw new ApiClientError("unexpected", "The OCR service returned an unreadable response."); }
  if (!response.ok) {
    if (response.status === 422) throw new ApiClientError("validation", validationMessage(body));
    if (response.status === 429) throw new ApiClientError("unavailable", "Too many OCR requests. Wait briefly before trying again.");
    if (response.status === 503) throw new ApiClientError("unavailable", "OCR is unavailable or busy. Wait briefly and try again.");
    throw new ApiClientError("server", "Text extraction could not be completed. Please try again.");
  }
  if (!isOcrResult(body)) throw new ApiClientError("unexpected", "The OCR service returned an unexpected response.");
  return body;
}

export async function getPerformance(): Promise<PerformanceReport> {
  let response: Response;
  try { response = await fetchWithTimeout(`${API_BASE_URL}/api/performance`, { method: "GET", headers: { Accept: "application/json" } }, API_TIMEOUT_MS.performance, "The performance request timed out. Please try again."); }
  catch (error) {
    if (error instanceof ApiClientError) throw error;
    throw new ApiClientError("unavailable", "The ScamLens API is unavailable. Check the API connection and try again.");
  }
  let body: unknown;
  try { body = await response.json(); }
  catch { throw new ApiClientError("unexpected", "The performance service returned an unreadable response."); }
  if (!response.ok) {
    if (response.status === 429) throw new ApiClientError("unavailable", "Too many requests. Wait briefly before trying again.");
    if (response.status === 503) throw new ApiClientError("unavailable", "Stored performance results are unavailable.");
    throw new ApiClientError("server", "Stored performance results could not be loaded.");
  }
  if (!isPerformanceReport(body)) throw new ApiClientError("unexpected", "The performance service returned an unexpected response.");
  return body;
}
