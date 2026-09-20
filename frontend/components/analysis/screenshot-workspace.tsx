"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import { EmailResult } from "@/components/analysis/email-workspace";
import { MessageResult } from "@/components/analysis/message-workspace";
import { ResultError } from "@/components/analysis/result-ui";
import { PageHeader, StatePanel } from "@/components/ui";
import { analyzeEmail, analyzeMessage, EMAIL_MAX_CHARACTERS, extractScreenshotText, MESSAGE_MAX_CHARACTERS, normalizeApiError, SCREENSHOT_ACCEPT, SCREENSHOT_MAX_BYTES, type EmailAnalysis, type MessageAnalysis, type OcrResult } from "@/lib/api";

type Phase = "idle" | "loading" | "error" | "success";
type AnalysisType = "message" | "email";
type ScreenshotAnalysis = { type: "message"; value: MessageAnalysis } | { type: "email"; value: EmailAnalysis };
const ACCEPT = SCREENSHOT_ACCEPT.join(",");

export function ScreenshotWorkspace() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [ocrState, setOcrState] = useState<Phase>("idle");
  const [ocr, setOcr] = useState<OcrResult | null>(null);
  const [reviewedText, setReviewedText] = useState("");
  const [analysisState, setAnalysisState] = useState<Phase>("idle");
  const [analysisType, setAnalysisType] = useState<AnalysisType | null>(null);
  const [result, setResult] = useState<ScreenshotAnalysis | null>(null);
  const [error, setError] = useState<{ title: string; message: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const ocrGeneration = useRef(0);
  const analysisGeneration = useRef(0);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function chooseFile(next: File | null) {
    ocrGeneration.current += 1; analysisGeneration.current += 1;
    if (preview) URL.revokeObjectURL(preview);
    setPreview(null); setFile(null); setOcr(null); setReviewedText(""); setResult(null); setAnalysisType(null);
    setOcrState("idle"); setAnalysisState("idle"); setError(null);
    if (!next) return;
    if (!SCREENSHOT_ACCEPT.includes(next.type as (typeof SCREENSHOT_ACCEPT)[number])) {
      setError({ title: "Unsupported image format", message: "Choose a PNG, JPEG/JPG, or WEBP image." }); setOcrState("error"); return;
    }
    if (next.size > SCREENSHOT_MAX_BYTES) {
      setError({ title: "Image is too large", message: "Choose an image no larger than 5 MiB. The API also validates decoded dimensions up to 20 megapixels." }); setOcrState("error"); return;
    }
    setFile(next); setPreview(URL.createObjectURL(next));
  }

  async function runOcr() {
    if (!file || ocrState === "loading") return;
    setOcrState("loading"); setOcr(null); setReviewedText(""); setResult(null); setAnalysisType(null); setAnalysisState("idle"); setError(null);
    const generation = ++ocrGeneration.current;
    try {
      const response = await extractScreenshotText(file);
      if (generation !== ocrGeneration.current) return;
      setOcr(response); setReviewedText(response.extracted_text); setOcrState("success");
    } catch (caught) {
      if (generation !== ocrGeneration.current) return;
      const value = normalizeApiError(caught);
      setError({ title: value.kind === "validation" ? "Screenshot rejected" : value.kind === "unavailable" ? "OCR unavailable" : "Text extraction unsuccessful", message: value.message }); setOcrState("error");
    }
  }

  function updateReview(value: string) {
    analysisGeneration.current += 1;
    setReviewedText(value);
    if (result || analysisState !== "idle") { setResult(null); setAnalysisState("idle"); setError(null); }
  }

  async function analyze(type: AnalysisType) {
    if (!reviewedText.trim()) { setError({ title: "No reviewed text", message: "Correct or enter usable English text before analysis." }); setAnalysisState("error"); return; }
    if (type === "message" && reviewedText.length > MESSAGE_MAX_CHARACTERS) { setResult(null); setAnalysisType(type); setError({ title: "Text is too long for Message Analysis", message: `The SMS baseline accepts up to ${MESSAGE_MAX_CHARACTERS.toLocaleString()} characters. Shorten the reviewed text or analyze it as an email.` }); setAnalysisState("error"); return; }
    setAnalysisType(type); setAnalysisState("loading"); setResult(null); setError(null);
    const generation = ++analysisGeneration.current;
    try {
      const response = type === "message" ? await analyzeMessage(reviewedText) : await analyzeEmail("", reviewedText);
      if (generation !== analysisGeneration.current) return;
      setResult(type === "message" ? { type, value: response as MessageAnalysis } : { type, value: response as EmailAnalysis }); setAnalysisState("success");
    }
    catch (caught) { if (generation !== analysisGeneration.current) return; const value = normalizeApiError(caught); setError({ title: value.kind === "unavailable" ? "Analysis service unavailable" : "Analysis unsuccessful", message: value.message }); setAnalysisState("error"); }
  }

  function drop(event: DragEvent<HTMLDivElement>) { event.preventDefault(); chooseFile(event.dataTransfer.files.item(0)); }
  function inputChanged(event: ChangeEvent<HTMLInputElement>) { chooseFile(event.target.files?.[0] ?? null); event.target.value = ""; }

  const currentStep = result ? 5 : analysisState === "loading" || analysisType ? 5 : ocr ? 3 : file ? 2 : 1;
  const workflowSteps = ["Upload", "OCR", "Review", "Choose type", "Result"];

  return <>
    <PageHeader eyebrow="Analysis / Screenshot" title="Screenshot Analysis" description="Upload a screenshot, extract English text with Tesseract, review it, then explicitly analyze the reviewed text."/>
    <nav aria-label="Screenshot analysis stages">
      <ol className="workflow-rail">{workflowSteps.map((step, index) => { const number = index + 1; const reached = number <= currentStep; return <li aria-current={number === currentStep ? "step" : undefined} className={reached ? "active" : ""} key={step}><span>{String(number).padStart(2, "0")}</span>{step}</li>; })}</ol>
    </nav>
    <section className="screenshot-grid">
      <div className="input-panel">
        <div className="input-panel-heading"><div><p className="panel-step">01 · Upload</p><h2>Select a screenshot</h2></div></div>
        <div className="upload-zone" onDragOver={(event) => event.preventDefault()} onDrop={drop}>
          <input ref={inputRef} accept={ACCEPT} aria-describedby={`screenshot-constraints screenshot-privacy${ocrState === "error" ? " screenshot-ocr-error" : ""}`} aria-invalid={ocrState === "error"} className="sr-only" id="screenshot-file" type="file" onChange={inputChanged}/>
          <label className="button button-secondary" htmlFor="screenshot-file">Choose image</label>
          <p>or drag and drop here</p><small id="screenshot-constraints">PNG, JPEG/JPG, or WEBP · 5 MiB max · 20 MP decoded max</small>
        </div>
        {file && <div className="selected-file"><div><strong>{file.name}</strong><span>{formatBytes(file.size)}</span></div><button className="button button-quiet" type="button" onClick={() => chooseFile(null)}>Remove image</button></div>}
        {preview && <div className="image-preview"><div aria-label="Browser preview of selected screenshot" className="image-preview-canvas" role="img" style={{ backgroundImage: `url(${preview})` }}/><p>Browser preview only. ScamLens does not assess image authenticity or manipulation.</p></div>}
        <p className="privacy-note" id="screenshot-privacy"><span aria-hidden="true">◇</span> Browser → configured ScamLens API → Tesseract OCR on the backend. This page does not intentionally persist your image or text.</p>
        <button className="button button-primary analyze-button" disabled={!file || ocrState === "loading" || analysisState === "loading"} type="button" onClick={runOcr}>{ocrState === "loading" ? "Extracting text…" : ocr ? "Run OCR again" : "Extract text"}<span aria-hidden="true">→</span></button>
      </div>
      <aside className="workspace-aside"><p className="panel-step">Scope</p><h2>What this does not determine</h2><p>OCR transcribes visible English text; it does not establish authenticity.</p><ul><li>Screenshot manipulation or sender identity</li><li>Brand or logo authenticity</li><li>QR-code or website safety</li></ul></aside>
    </section>
    <section aria-busy={ocrState === "loading"} aria-label="OCR status" aria-live="polite" className="result-region">
      {ocrState === "idle" && !file && <StatePanel tone="empty" title="Upload a screenshot to begin OCR" description="Choose a supported image. Text extraction starts only after you select Extract text."/>}
      {ocrState === "loading" && <StatePanel tone="loading" title="Extracting English text" description="The ScamLens API is processing the image with Tesseract. No classification is running."/>}
      {ocrState === "error" && error && <ResultError id="screenshot-ocr-error" title={error.title} message={error.message}/>} 
    </section>
    {ocr && <section className="review-panel">
      <div className="input-panel-heading"><div><p className="panel-step">02 · Human review</p><h2>Review and correct the extracted text before analysis</h2></div><span className="character-count">{reviewedText.length.toLocaleString()} / {EMAIL_MAX_CHARACTERS.toLocaleString()}</span></div>
      {!ocr.usable_text && <StatePanel tone="caution" title="No usable text was extracted" description="OCR could not find usable text. You may enter a faithful transcription manually, or choose another image."/>}
      <label htmlFor="reviewed-text">Editable extracted text</label>
      <textarea aria-describedby={`ocr-review-help${analysisState === "error" ? " screenshot-analysis-error" : ""}`} aria-invalid={analysisState === "error"} id="reviewed-text" maxLength={EMAIL_MAX_CHARACTERS} rows={10} value={reviewedText} onChange={(event) => updateReview(event.target.value)}/>
      <p className="supporting-copy" id="ocr-review-help">OCR can omit, substitute, merge, or invent characters. The exact reviewed text shown here—not hidden original OCR text—is submitted when you analyze.</p>
      <fieldset className="analysis-type-choice"><legend>What kind of content is shown in the screenshot?</legend><p>Your choice determines which existing experimental model analyzes the reviewed text. ScamLens does not choose automatically.</p><div>
        <button className="analysis-choice" disabled={analysisState === "loading" || ocrState === "loading"} type="button" onClick={() => analyze("message")}><strong>{analysisState === "loading" && analysisType === "message" ? "Analyzing as Message…" : "Analyze as Message"}</strong><span>Experimental English SMS spam/ham baseline</span></button>
        <button className="analysis-choice" disabled={analysisState === "loading" || ocrState === "loading"} type="button" onClick={() => analyze("email")}><strong>{analysisState === "loading" && analysisType === "email" ? "Analyzing as Email…" : "Analyze as Email"}</strong><span>Experimental three-class email model; reviewed text becomes the body</span></button>
      </div></fieldset>
    </section>}
    <section aria-busy={analysisState === "loading"} aria-label="Reviewed text analysis result" aria-live="polite" className="result-region">
      {ocr && analysisState === "idle" && <StatePanel tone="empty" title="Review and choose an analysis type" description="No classification has run. Correct the extracted text, then explicitly choose Message or Email analysis."/>}
      {analysisState === "loading" && <StatePanel tone="loading" title={`Analyzing as ${analysisType === "email" ? "Email" : "Message"}`} description={`The existing experimental ${analysisType === "email" ? "email" : "SMS spam/ham"} model is processing the exact text you reviewed.`}/>} 
      {analysisState === "error" && error && <ResultError id="screenshot-analysis-error" title={error.title} message={error.message}/>} 
      {analysisState === "success" && result && <p className="analysis-context"><span>Analysis context</span><strong>Analyzed as {result.type === "email" ? "Email" : "Message"}</strong></p>}
      {analysisState === "success" && result?.type === "message" && <MessageResult result={result.value} source="screenshot"/>} 
      {analysisState === "success" && result?.type === "email" && <EmailResult result={result.value}/>} 
    </section>
  </>;
}

function formatBytes(bytes: number) { return `${(bytes / 1024 / 1024).toFixed(2)} MiB`; }
