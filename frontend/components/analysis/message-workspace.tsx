"use client";

import { FormEvent, useRef, useState } from "react";
import { AnalysisResultShell, ResultError, ResultHeading, ResultPanel, ScopeDetails, ScoreBar } from "@/components/analysis/result-ui";
import { PageHeader, StatePanel } from "@/components/ui";
import { analyzeMessage, MESSAGE_MAX_CHARACTERS, normalizeApiError, type MessageAnalysis } from "@/lib/api";

type RequestState = "idle" | "loading" | "error" | "success";

export function MessageWorkspace() {
  const [text, setText] = useState("");
  const [state, setState] = useState<RequestState>("idle");
  const [result, setResult] = useState<MessageAnalysis | null>(null);
  const [error, setError] = useState<{ title: string; message: string } | null>(null);
  const requestGeneration = useRef(0);

  function updateText(value: string) {
    requestGeneration.current += 1;
    setText(value);
    setResult(null); setError(null); setState("idle");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim()) {
      setResult(null); setState("error");
      setError({ title: "Enter a message", message: "Paste suspicious English message text before starting the analysis." });
      return;
    }
    const generation = ++requestGeneration.current;
    const submittedText = text;
    setState("loading"); setResult(null); setError(null);
    try {
      const response = await analyzeMessage(submittedText);
      if (generation !== requestGeneration.current) return;
      setResult(response); setState("success");
    } catch (caught) {
      if (generation !== requestGeneration.current) return;
      const apiError = normalizeApiError(caught);
      setError({ title: apiError.kind === "unavailable" ? "Analysis service unavailable" : apiError.kind === "validation" ? "Check your message" : "Analysis unsuccessful", message: apiError.message });
      setState("error");
    }
  }

  return <>
    <PageHeader eyebrow="Analysis / Message" title="Message Analysis" description="Paste a suspicious English message to inspect it."/>
    <div className="workspace-layout message-workspace-layout">
      <form aria-describedby="message-privacy" className="input-panel" onSubmit={submit}>
        <div className="input-panel-heading"><div><p className="panel-step">01 · Add content</p><h2>Message text</h2></div><span className="character-count" data-limit={text.length === MESSAGE_MAX_CHARACTERS}>{text.length.toLocaleString()} / {MESSAGE_MAX_CHARACTERS.toLocaleString()}</span></div>
        <label htmlFor="message-text">Message text <span>English SMS-style content</span></label>
        <textarea aria-describedby={`message-help message-privacy${state === "error" ? " message-error" : ""}`} aria-invalid={state === "error"} autoComplete="off" id="message-text" maxLength={MESSAGE_MAX_CHARACTERS} onChange={(event) => updateText(event.target.value)} placeholder="Paste the message you want to inspect…" rows={7} value={text}/>
        <p className="field-help" id="message-help">ScamLens classifies the submitted text only; it does not inspect the sender or open links.</p>
        <p className="privacy-note" id="message-privacy"><span aria-hidden="true">◇</span> Sent to the configured ScamLens API for analysis. This page does not intentionally store your text.</p>
        <button className="button button-primary analyze-button" disabled={state === "loading"} type="submit">{state === "loading" ? "Analyzing message…" : "Analyze message"}<span aria-hidden="true">→</span></button>
      </form>

      <aside className="workspace-aside" aria-label="Message analysis scope"><p className="panel-step">Before you analyze</p><h2>What this checks</h2><p>This experimental model classifies English SMS-style text as spam or ham (non-spam).</p><ul><li>It is not a phishing or fraud detector.</li><li>A ham result cannot confirm safety.</li><li>No links or external services are opened.</li></ul></aside>
    </div>

    <section aria-busy={state === "loading"} aria-label="Message analysis result" aria-live="polite" className="result-region">
      {state === "idle" && <StatePanel tone="empty" title="Paste a message to begin analysis" description="The experimental spam/ham output will appear here after you explicitly submit the text."/>}
      {state === "loading" && <StatePanel tone="loading" title="Analyzing message" description="The ScamLens API is processing the submitted text with the existing model."/>}
      {state === "error" && error && <ResultError id="message-error" title={error.title} message={error.message}/>} 
      {state === "success" && result && <MessageResult result={result}/>} 
    </section>
  </>;
}

export function MessageResult({ result, source = "message" }: { result: MessageAnalysis; source?: "message" | "screenshot" }) {
  const label = result.prediction === "spam" ? "Spam" : "Ham (non-spam)";
  const context = result.prediction === "spam"
    ? "The classifier identified spam-like patterns in this message. This is classifier evidence, not proof of fraud or malicious intent."
    : "This classifier did not classify the message as spam. This does not confirm that the message is safe, authentic, or trustworthy.";
  return <AnalysisResultShell>
    <ResultHeading label={label} context={context} tone={result.prediction === "spam" ? "caution" : "neutral"}/>
    <div className="result-grid">
      <ResultPanel category="Model output" title={source === "screenshot" ? "Experimental English SMS baseline" : "Spam model score"} tone="model">
        <ScoreBar label="Spam score" value={result.scores.spam} marker={result.scores.threshold} markerLabel={`Classification threshold: ${result.scores.threshold.toFixed(2)}`}/>
        <p className="supporting-copy">This score is a classifier output. It is not a probability of fraud, harm, authenticity, or safety.</p>
      </ResultPanel>
      <ResultPanel category="Limitations" title="Keep this result in scope" tone="limitation">
        <ul className="limitation-list">{result.limitations.map((item) => <li key={item}>{item}</li>)}</ul>
      </ResultPanel>
    </div>
    <ResultPanel category="Verification" title="Use this as one limited signal" tone="guidance">
      <p className="result-panel-copy">Verify suspicious requests through an independent trusted channel. {source === "screenshot" ? "The result cannot confirm that the screenshot, sender, or extracted text is authentic." : "Do not treat the classification as confirmation that the message or sender is safe."}</p>
    </ResultPanel>
    <ScopeDetails summary="How this output was produced"><p>The existing model compares its spam score with the configured threshold. ScamLens does not recalibrate or reinterpret that output in the browser.</p></ScopeDetails>
  </AnalysisResultShell>;
}
