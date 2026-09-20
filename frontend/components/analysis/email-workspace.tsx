"use client";

import { FormEvent, useRef, useState } from "react";
import { AnalysisResultShell, NumberedList, ResultError, ResultHeading, ResultPanel, ScopeDetails, ScoreBar } from "@/components/analysis/result-ui";
import { StatusBadge } from "@/components/status-badge";
import { InfoCallout, PageHeader, StatePanel } from "@/components/ui";
import { analyzeEmail, EMAIL_MAX_CHARACTERS, normalizeApiError, type EmailAnalysis } from "@/lib/api";

type RequestState = "idle" | "loading" | "error" | "success";

export function EmailWorkspace() {
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [state, setState] = useState<RequestState>("idle");
  const [result, setResult] = useState<EmailAnalysis | null>(null);
  const [error, setError] = useState<{ title: string; message: string } | null>(null);
  const requestGeneration = useRef(0);
  const totalCharacters = subject.length + body.length;

  function invalidate() {
    requestGeneration.current += 1;
    setResult(null); setError(null); setState("idle");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!subject.trim() && !body.trim()) {
      setResult(null); setState("error");
      setError({ title: "Enter email content", message: "Add a subject or body before starting the analysis." });
      return;
    }
    if (totalCharacters > EMAIL_MAX_CHARACTERS) {
      setResult(null); setState("error");
      setError({ title: "Email is too long", message: `Subject and body together must be ${EMAIL_MAX_CHARACTERS.toLocaleString()} characters or fewer.` });
      return;
    }
    const generation = ++requestGeneration.current;
    const submittedSubject = subject;
    const submittedBody = body;
    setState("loading"); setResult(null); setError(null);
    try {
      const response = await analyzeEmail(submittedSubject, submittedBody);
      if (generation !== requestGeneration.current) return;
      setResult(response); setState("success");
    } catch (caught) {
      if (generation !== requestGeneration.current) return;
      const apiError = normalizeApiError(caught);
      setError({ title: apiError.kind === "unavailable" ? "Analysis service unavailable" : apiError.kind === "validation" ? "Check the email content" : "Analysis unsuccessful", message: apiError.message });
      setState("error");
    }
  }

  return <>
    <PageHeader eyebrow="Analysis / Email" title="Email Analysis" description="Review a suspicious email using an experimental three-class model and deterministic textual indicators."><div className="header-status"><StatusBadge tone="caution">Experimental</StatusBadge><span>Within-corpus evaluation only</span></div></PageHeader>
    <div className="workspace-layout email-workspace-layout">
      <form aria-describedby="email-privacy" className="input-panel" onSubmit={submit}>
        <div className="input-panel-heading"><div><p className="panel-step">01 · Add content</p><h2>Email text</h2></div><span className="character-count" data-limit={totalCharacters > EMAIL_MAX_CHARACTERS}>{totalCharacters.toLocaleString()} / {EMAIL_MAX_CHARACTERS.toLocaleString()}</span></div>
        <label htmlFor="email-subject">Subject <span>optional if body is provided</span></label>
        <input aria-describedby={`email-privacy${state === "error" ? " email-error" : ""}`} aria-invalid={state === "error"} autoComplete="off" id="email-subject" maxLength={EMAIL_MAX_CHARACTERS} onChange={(event) => { setSubject(event.target.value); invalidate(); }} placeholder="Paste the email subject…" type="text" value={subject}/>
        <label htmlFor="email-body">Body <span>optional if subject is provided</span></label>
        <textarea aria-describedby={`email-privacy${state === "error" ? " email-error" : ""}`} aria-invalid={state === "error"} autoComplete="off" id="email-body" maxLength={EMAIL_MAX_CHARACTERS} onChange={(event) => { setBody(event.target.value); invalidate(); }} placeholder="Paste the email body…" rows={6} value={body}/>
        <p className="privacy-note" id="email-privacy"><span aria-hidden="true">◇</span> Sent to the configured ScamLens API for analysis. This page does not intentionally store the subject or body.</p>
        <button className="button button-primary analyze-button" disabled={state === "loading" || totalCharacters > EMAIL_MAX_CHARACTERS} type="submit">{state === "loading" ? "Analyzing email…" : "Analyze email"}<span aria-hidden="true">→</span></button>
      </form>
      <aside className="workspace-aside" aria-label="Email analysis scope"><p className="panel-step">Two separate signals</p><h2>Prediction and observations</h2><p>The model prediction and deterministic text indicators are displayed separately. Indicators never replace or modify the prediction.</p><ul><li>No links or attachments are inspected.</li><li>Sender identity and headers are not verified.</li><li>A Valid output cannot confirm safety.</li></ul></aside>
    </div>
    <section aria-busy={state === "loading"} aria-label="Email analysis result" aria-live="polite" className="result-region">
      {state === "idle" && <StatePanel tone="empty" title="Enter email content to begin analysis" description="Model output, observed indicators, and verification guidance will appear here after you explicitly submit the email."/>}
      {state === "loading" && <StatePanel tone="loading" title="Analyzing email" description="The ScamLens API is processing the subject and body with the existing model and observation rules."/>}
      {state === "error" && error && <ResultError id="email-error" title={error.title} message={error.message}/>} 
      {state === "success" && result && <EmailResult result={result}/>} 
    </section>
  </>;
}

export function EmailResult({ result }: { result: EmailAnalysis }) {
  return <AnalysisResultShell>
    <ResultHeading label={result.prediction} context={result.prediction === "Valid" ? "A Valid model output does not confirm that this email is safe or authentic." : "This is an experimental classifier output, not a definitive fraud or safety determination."} tone={result.prediction === "Valid" ? "neutral" : "caution"}/>
    <div className="result-grid">
      <ResultPanel category="Model output" title="Classifier outputs" tone="model"><p className="supporting-copy">Returned model scores—not calibrated probabilities of safety, fraud, or harm.</p>{(["Valid", "Spam", "Phishing"] as const).map((label) => <ScoreBar key={label} label={label} value={result.classifier_outputs[label]}/>)}</ResultPanel>
      <ResultPanel category="Observed indicators" title="Text-pattern observations" tone="observation"><p className="supporting-copy">Deterministic observations are separate from the model output.</p>{result.observed_indicators.length ? <ul className="indicator-list">{result.observed_indicators.map((item) => <li key={item}>{item}</li>)}</ul> : <div className="no-indicators"><strong>No supported textual indicators were detected.</strong><p>This does not confirm that the email is safe.</p></div>}</ResultPanel>
    </div>
    {result.disagreement && result.disagreement_message && <InfoCallout className="disagreement-callout" title="Model / evidence disagreement" tone="warning"><p>{result.disagreement_message}</p><p>The observed indicators do not change the model prediction.</p></InfoCallout>}
    <ResultPanel category="Verification" title="What you can do next" tone="guidance"><NumberedList items={result.verification_guidance}/></ResultPanel>
    <ScopeDetails summary="Experimental scope and limitations"><p><strong>Evaluation scope:</strong> within corpus only</p><p><strong>Generalization status:</strong> not established</p><ul className="limitation-list">{result.limitations.map((item) => <li key={item}>{item}</li>)}</ul></ScopeDetails>
  </AnalysisResultShell>;
}
