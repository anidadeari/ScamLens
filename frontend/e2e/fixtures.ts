import type { Page, Route } from "@playwright/test";

export const messageResult = {
  analysis_type: "message", prediction: "spam",
  scores: { spam: 0.82, threshold: 0.61 }, interpretation: "test",
  limitations: ["English SMS corpus only."],
};

export const hamResult = { ...messageResult, prediction: "ham", scores: { spam: 0.12, threshold: 0.61 } };

export const emailResult = {
  analysis_type: "email", prediction: "Valid",
  classifier_outputs: { Valid: 0.7, Spam: 0.2, Phishing: 0.1 },
  observed_indicators: ["Urgency language was observed."], disagreement: true,
  disagreement_message: "The prediction and observed indicators differ.",
  verification_guidance: ["Contact the sender independently."], limitations: ["Within-corpus only."],
  evaluation_scope: "within_corpus_only", generalization_status: "not_established",
};

export const urlResult = {
  analysis_type: "url", prediction: "benign",
  classifier_outputs: { benign: 0.8, phish: 0.2 }, observed_indicators: [], disagreement: false,
  disagreement_message: null, verification_guidance: ["Verify through a trusted channel."],
  limitations: ["String-only analysis."],
};

export const performanceResult = {
  source: "stored_artifacts", experiments_are_directly_comparable: false,
  message: { experiment: "SMS baseline", evaluation_scope: "held_out_sms_test_split", accuracy: 0.9811, macro_f1: 0.9492, target_recall_label: "Spam", target_recall: 0.913, limitations: ["Corpus-specific."] },
  email: { experiment: "Email baseline", evaluation_scope: "within_corpus_only", accuracy: 0.921, macro_f1: 0.899, target_recall_label: "Phishing", target_recall: 0.88, limitations: ["Generalization is not established."] },
  url: { experiment: "URL baseline", evaluation_scope: "filtered_official_temporal_test", accuracy: 0.971, macro_f1: 0.969, target_recall_label: "Phishing", target_recall: 0.963, limitations: ["URL text only."] },
};

export async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

export async function mockHealth(page: Page) {
  await page.route("**/api/health", (route) => json(route, { status: "ok" }));
}

export const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", "base64");
