import { expect, test } from "@playwright/test";
import axe from "axe-core";
import { emailResult, hamResult, json, messageResult, mockHealth, performanceResult, png, urlResult } from "./fixtures";

test.beforeEach(async ({ page }) => mockHealth(page));

test("all six routes render their primary heading and navigation", async ({ page }) => {
  for (const [path, heading] of [["/", "Analyze suspicious content with evidence in view."], ["/message", "Message Analysis"], ["/email", "Email Analysis"], ["/screenshot", "Screenshot Analysis"], ["/url", "URL Analysis"], ["/performance", "Model Performance"]]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
  }
});

test.describe("message", () => {
  test.beforeEach(async ({ page }) => page.goto("/message"));

  test("validates empty and constrains oversized input", async ({ page }) => {
    await page.getByRole("button", { name: /Analyze message/ }).click();
    await expect(page.getByText("Enter a message", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Message text", { exact: false })).toHaveAttribute("maxlength", "5000");
    await expect(page.getByLabel("Message text", { exact: false })).toHaveAttribute("aria-invalid", "true");
  });

  test("shows loading, prevents duplicate submit, and distinguishes score from threshold", async ({ page }) => {
    let resolve!: () => void;
    const gate = new Promise<void>((done) => { resolve = done; });
    let calls = 0;
    await page.route("**/api/analyze/message", async (route) => { calls += 1; await gate; await json(route, messageResult); });
    await page.getByLabel("Message text", { exact: false }).fill("Limited-time prize claim");
    await page.getByRole("button", { name: /Analyze message/ }).click();
    await expect(page.getByText("Analyzing message", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: /Analyzing message/ })).toBeDisabled();
    resolve();
    await expect(page.getByRole("heading", { name: "Spam", exact: true })).toBeVisible();
    expect(calls).toBe(1);
    await expect(page.getByText("Spam score", { exact: true })).toBeVisible();
    await expect(page.getByText("Classification threshold: 0.61")).toBeVisible();
    await expect(page.getByText(/not proof of fraud or malicious intent/)).toBeVisible();
  });

  test("ham is not represented as safe and editing invalidates a result", async ({ page }) => {
    await page.route("**/api/analyze/message", (route) => json(route, hamResult));
    const input = page.getByLabel("Message text", { exact: false });
    await input.fill("Hello"); await page.getByRole("button", { name: /Analyze message/ }).click();
    await expect(page.getByRole("heading", { name: "Ham (non-spam)" })).toBeVisible();
    await expect(page.getByText(/does not confirm that the message is safe/)).toBeVisible();
    await input.fill("Edited");
    await expect(page.getByRole("heading", { name: "Ham (non-spam)" })).toHaveCount(0);
  });

  test("stale response cannot overwrite newer content", async ({ page }) => {
    await page.route("**/api/analyze/message", async (route) => { await new Promise((r) => setTimeout(r, 250)); await json(route, messageResult); });
    const input = page.getByLabel("Message text", { exact: false });
    await input.fill("first"); await page.getByRole("button", { name: /Analyze message/ }).click(); await input.fill("newer");
    await page.waitForTimeout(350);
    await expect(page.getByRole("heading", { name: "Spam", exact: true })).toHaveCount(0);
    await expect(page.getByText("Paste a message to begin analysis")).toBeVisible();
  });
});

test.describe("email", () => {
  test.beforeEach(async ({ page }) => page.goto("/email"));

  test("requires content and exposes combined size limit", async ({ page }) => {
    await page.getByRole("button", { name: /Analyze email/ }).click();
    await expect(page.getByText("Enter email content", { exact: true })).toBeVisible();
    await expect(page.locator("#email-subject")).toHaveAttribute("maxlength", "100000");
    await expect(page.locator("#email-body")).toHaveAttribute("maxlength", "100000");
    await page.locator("#email-subject").fill("s".repeat(50_001));
    await page.locator("#email-body").fill("b".repeat(50_000));
    await expect(page.getByRole("button", { name: /Analyze email/ })).toBeDisabled();
    await expect(page.getByText("100,001 / 100,000")).toBeVisible();
  });

  test("renders all model outputs separately from deterministic observations and disagreement", async ({ page }) => {
    await page.route("**/api/analyze/email", (route) => json(route, emailResult));
    await page.locator("#email-subject").fill("Urgent account notice");
    await page.locator("#email-body").fill("Review this request");
    await page.getByRole("button", { name: /Analyze email/ }).click();
    await expect(page.getByRole("heading", { name: "Valid" })).toBeVisible();
    for (const label of ["Valid", "Spam", "Phishing"]) await expect(page.getByText(label, { exact: true }).last()).toBeVisible();
    await expect(page.getByText("Deterministic observations are separate from the model output.")).toBeVisible();
    await expect(page.getByText("Model / evidence disagreement")).toBeVisible();
    await expect(page.getByText(/does not confirm that this email is safe or authentic/)).toBeVisible();
  });

  test("editing invalidates result and an in-flight response is stale", async ({ page }) => {
    await page.route("**/api/analyze/email", async (route) => { await new Promise((r) => setTimeout(r, 200)); await json(route, emailResult); });
    const body = page.locator("#email-body");
    await body.fill("first"); await page.getByRole("button", { name: /Analyze email/ }).click(); await body.fill("newer");
    await page.waitForTimeout(300); await expect(page.getByRole("heading", { name: "Valid" })).toHaveCount(0);
  });
});

test.describe("screenshot", () => {
  test.beforeEach(async ({ page }) => page.goto("/screenshot"));

  test("rejects unsupported and oversized files before OCR", async ({ page }) => {
    const input = page.locator("#screenshot-file");
    await input.setInputFiles({ name: "bad.txt", mimeType: "text/plain", buffer: Buffer.from("bad") });
    await expect(page.getByText("Unsupported image format")).toBeVisible();
    await input.setInputFiles({ name: "large.png", mimeType: "image/png", buffer: Buffer.alloc(5 * 1024 * 1024 + 1) });
    await expect(page.getByText("Image is too large")).toBeVisible();
  });

  test("complete OCR review to explicit Message flow", async ({ page }) => {
    await page.route("**/api/ocr", (route) => json(route, { analysis_type: "ocr", extracted_text: "Prize claim", usable_text: true, classification_performed: false, review_required: true, limitations: ["OCR can make mistakes."] }));
    await page.route("**/api/analyze/message", (route) => json(route, messageResult));
    await page.locator("#screenshot-file").setInputFiles({ name: "shot.png", mimeType: "image/png", buffer: png });
    await expect(page.getByText(/does not assess image authenticity/)).toBeVisible();
    await page.getByRole("button", { name: /Extract text/ }).click();
    const review = page.getByLabel("Editable extracted text"); await expect(review).toHaveValue("Prize claim");
    await expect(page.getByText(/OCR can omit, substitute, merge, or invent/)).toBeVisible();
    await expect(page.getByText(/does not choose automatically/)).toBeVisible();
    await review.fill("Corrected prize claim");
    await page.getByRole("button", { name: /Analyze as Message/ }).click();
    await expect(page.getByText("Analyzed as Message")).toBeVisible();
    await review.fill("Edited again"); await expect(page.getByText("Analyzed as Message")).toHaveCount(0);
  });

  test("supports explicit Email flow and empty OCR review", async ({ page }) => {
    await page.route("**/api/ocr", (route) => json(route, { analysis_type: "ocr", extracted_text: "", usable_text: false, classification_performed: false, review_required: true, limitations: [] }));
    await page.route("**/api/analyze/email", (route) => json(route, emailResult));
    await page.locator("#screenshot-file").setInputFiles({ name: "shot.png", mimeType: "image/png", buffer: png });
    await page.getByRole("button", { name: /Extract text/ }).click();
    await expect(page.getByText("No usable text was extracted")).toBeVisible();
    await page.getByRole("button", { name: /Analyze as Email/ }).click(); await expect(page.getByText("No reviewed text")).toBeVisible();
    await page.getByLabel("Editable extracted text").fill("Manually reviewed email");
    await page.getByRole("button", { name: /Analyze as Email/ }).click(); await expect(page.getByText("Analyzed as Email")).toBeVisible();
  });

  test("OCR failure is sanitized and changing image invalidates OCR/result", async ({ page }) => {
    await page.route("**/api/ocr", (route) => json(route, { detail: "/srv/secret stack trace" }, 500));
    const input = page.locator("#screenshot-file"); await input.setInputFiles({ name: "shot.png", mimeType: "image/png", buffer: png });
    await page.getByRole("button", { name: /Extract text/ }).click(); await expect(page.getByText("Text extraction could not be completed. Please try again.")).toBeVisible();
    await expect(page.getByText(/\/srv\/secret/)).toHaveCount(0);
    await input.setInputFiles({ name: "other.png", mimeType: "image/png", buffer: png }); await expect(page.getByText("Text extraction could not be completed. Please try again.")).toHaveCount(0);
  });
});

test.describe("URL", () => {
  test.beforeEach(async ({ page }) => page.goto("/url"));

  test("validates input and boundary without making submitted destination clickable", async ({ page }) => {
    await page.getByRole("button", { name: /Analyze URL/ }).click(); await expect(page.getByText("Enter a URL", { exact: true })).toBeVisible();
    await expect(page.getByLabel("Full URL", { exact: false })).toHaveAttribute("maxlength", "2048");
    await page.route("**/api/analyze/url", (route) => json(route, urlResult));
    const inert = "https://192.0.2.1/never-fetch";
    await page.getByLabel("Full URL", { exact: false }).fill(inert); await page.getByRole("button", { name: /Analyze URL/ }).click();
    await expect(page.getByText(inert)).toBeVisible(); await expect(page.locator(`a[href="${inert}"]`)).toHaveCount(0);
    await expect(page.getByText(/Benign does not mean safe, verified, or trusted/)).toBeVisible();
    await expect(page.getByText(/No website content, redirects, DNS, WHOIS, reputation, ownership, or certificates/)).toBeVisible();
  });

  test("never requests submitted destination", async ({ page }) => {
    const requests: string[] = []; page.on("request", (request) => requests.push(request.url()));
    await page.route("**/api/analyze/url", (route) => json(route, { ...urlResult, prediction: "phish" }));
    await page.getByLabel("Full URL", { exact: false }).fill("https://203.0.113.77/trap"); await page.getByRole("button", { name: /Analyze URL/ }).click();
    await expect(page.getByRole("heading", { name: "Phishing" })).toBeVisible();
    await expect(page.getByText(/not proof that a website is malicious/)).toBeVisible();
    expect(requests.some((value) => value.startsWith("https://203.0.113.77"))).toBe(false);
    await expect(page.locator("link[rel~='icon']")).toHaveCount(0);
  });

  test("shows a sanitized validation error for a malformed URL", async ({ page }) => {
    await page.route("**/api/analyze/url", (route) => json(route, { detail: [{ message: "URL must include an http:// or https:// scheme." }] }, 422));
    await page.getByLabel("Full URL", { exact: false }).fill("example.invalid/path");
    await page.getByRole("button", { name: /Analyze URL/ }).click();
    await expect(page.getByText("Check the URL string")).toBeVisible();
    await expect(page.getByText(/must include an http:\/\/ or https:\/\/ scheme/)).toBeVisible();
  });
});

test("performance renders three unranked stored experiments with limitations", async ({ page }) => {
  await page.route("**/api/performance", (route) => json(route, performanceResult)); await page.goto("/performance");
  for (const heading of ["Message / SMS spam–ham experiment", "Email three-class experiment", "URL phishing–benign experiment"]) await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  await expect(page.getByText("0.9811")).toBeVisible(); await expect(page.getByText("0.9210")).toBeVisible(); await expect(page.getByText("0.9710")).toBeVisible();
  await expect(page.getByText(/not directly comparable and must not be used to rank/)).toBeVisible();
  await expect(page.getByText("Metrics not exposed by this API")).toBeVisible();
  await expect(page.getByText(/overall ScamLens accuracy/i)).toHaveCount(0);
});

for (const scenario of [
  ["HTTP 422", 422, { detail: [{ message: "Input is invalid." }] }, "Input is invalid."],
  ["HTTP 429", 429, { detail: "internal limiter key" }, "Too many requests"],
  ["HTTP 500", 500, { detail: "Traceback /home/private secret" }, "could not be completed"],
  ["malformed JSON", 200, "not-json", "unreadable response"],
] as const) {
  test(`sanitizes ${scenario[0]} analysis failures`, async ({ page }) => {
    await page.route("**/api/analyze/message", (route) => route.fulfill({ status: scenario[1], contentType: "application/json", body: typeof scenario[2] === "string" ? scenario[2] : JSON.stringify(scenario[2]) }));
    await page.goto("/message"); await page.getByLabel("Message text", { exact: false }).fill("test"); await page.getByRole("button", { name: /Analyze message/ }).click();
    await expect(page.getByText(new RegExp(scenario[3], "i"))).toBeVisible(); await expect(page.getByText(/Traceback|\/home\/private|internal limiter key/)).toHaveCount(0);
  });
}

test("backend unavailable is sanitized", async ({ page }) => {
  await page.route("**/api/analyze/message", (route) => route.abort("connectionrefused")); await page.goto("/message");
  await page.getByLabel("Message text", { exact: false }).fill("test"); await page.getByRole("button", { name: /Analyze message/ }).click();
  await expect(page.getByText(/ScamLens API is unavailable/)).toBeVisible();
});

test("schema-invalid successful response is sanitized", async ({ page }) => {
  await page.route("**/api/analyze/message", (route) => json(route, { analysis_type: "message", prediction: "spam", secret_path: "/private/model" }));
  await page.goto("/message"); await page.getByLabel("Message text", { exact: false }).fill("test"); await page.getByRole("button", { name: /Analyze message/ }).click();
  await expect(page.getByText(/unexpected response/)).toBeVisible(); await expect(page.getByText(/private\/model/)).toHaveCount(0);
});

for (const path of ["/", "/message", "/email", "/screenshot", "/url", "/performance"]) {
  test(`automated accessibility has no serious or critical violations on ${path}`, async ({ page }) => {
    if (path === "/performance") await page.route("**/api/performance", (route) => json(route, performanceResult));
    await page.goto(path); await page.addScriptTag({ content: axe.source });
    const violations = await page.evaluate(async () => (await window.axe.run(document, { resultTypes: ["violations"] })).violations.filter((item) => ["serious", "critical"].includes(item.impact ?? "")));
    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
  });
}

declare global { interface Window { axe: typeof axe } }
