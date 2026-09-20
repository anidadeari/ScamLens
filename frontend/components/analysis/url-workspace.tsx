"use client";

import { FormEvent, useRef, useState } from "react";
import { AnalysisResultShell, NumberedList, ResultError, ResultHeading, ResultPanel, ScopeDetails, ScoreBar } from "@/components/analysis/result-ui";
import { InfoCallout, PageHeader, StatePanel } from "@/components/ui";
import { analyzeUrl, normalizeApiError, URL_MAX_CHARACTERS, type UrlAnalysis } from "@/lib/api";

type Phase = "idle" | "loading" | "error" | "success";

export function UrlWorkspace() {
  const [url, setUrl] = useState(""); const [state, setState] = useState<Phase>("idle");
  const [result, setResult] = useState<UrlAnalysis | null>(null); const [error, setError] = useState<{ title: string; message: string } | null>(null);
  const requestGeneration = useRef(0);
  function update(value: string) { requestGeneration.current += 1; setUrl(value); if (result || error || state === "loading") { setResult(null); setError(null); setState("idle"); } }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!url) { setState("error"); setError({ title: "Enter a URL", message: "Enter the full URL string, including an HTTP or HTTPS scheme." }); return; }
    setState("loading"); setResult(null); setError(null);
    const generation = ++requestGeneration.current;
    try { const response = await analyzeUrl(url); if (generation !== requestGeneration.current) return; setResult(response); setState("success"); }
    catch (caught) { if (generation !== requestGeneration.current) return; const value = normalizeApiError(caught); setError({ title: value.kind === "validation" ? "Check the URL string" : value.kind === "unavailable" ? "URL analysis unavailable" : "Analysis unsuccessful", message: value.message }); setState("error"); }
  }
  return <>
    <PageHeader eyebrow="Analysis / URL" title="URL Analysis" description="Inspect a submitted URL as text with the existing experimental URL-string classifier."/>
    <InfoCallout title="String-only analysis" tone="warning"><p>ScamLens analyzes the characters and structure of the submitted URL. It does not visit the address.</p><p>No website content, redirects, DNS, WHOIS, reputation, ownership, or certificates are checked.</p></InfoCallout>
    <div className="workspace-layout url-input-layout">
      <form className="input-panel" onSubmit={submit}>
        <div className="input-panel-heading"><div><p className="panel-step">01 · Input</p><h2>URL string</h2></div><span className="character-count" data-limit={url.length === URL_MAX_CHARACTERS}>{url.length.toLocaleString()} / {URL_MAX_CHARACTERS.toLocaleString()}</span></div>
        <label htmlFor="url-input">Full URL <span>HTTP or HTTPS scheme required</span></label>
        <input aria-describedby={`url-privacy${state === "error" ? " url-error" : ""}`} aria-invalid={state === "error"} autoComplete="off" id="url-input" maxLength={URL_MAX_CHARACTERS} placeholder={`https${"://"}example.invalid/path?item=review`} value={url} onChange={(event) => update(event.target.value)}/>
        <p className="privacy-note" id="url-privacy"><span aria-hidden="true">◇</span> The string is sent to the configured ScamLens API. It is treated as data and is never opened.</p>
        <button className="button button-primary analyze-button" disabled={state === "loading"} type="submit">{state === "loading" ? "Analyzing URL string…" : "Analyze URL"}<span aria-hidden="true">→</span></button>
      </form>
      <aside className="workspace-aside"><p className="panel-step">Before you analyze</p><h2>What this checks</h2><p>The experimental model and deterministic observations inspect lexical patterns in the submitted characters.</p><ul><li>No website or redirect is opened.</li><li>No DNS, WHOIS, reputation, or ownership lookup runs.</li><li>HTTPS does not establish legitimacy.</li></ul></aside>
    </div>
    <section aria-busy={state === "loading"} aria-label="URL analysis result" aria-live="polite" className="result-region">
      {state === "idle" && <StatePanel tone="empty" title="Enter a URL to analyze its string features" description="The address will be treated as text and will not be visited."/>}
      {state === "loading" && <StatePanel tone="loading" title="Analyzing URL string" description="The ScamLens API is inspecting the submitted characters. It is not visiting the address."/>}
      {state === "error" && error && <ResultError id="url-error" title={error.title} message={error.message}/>} 
      {state === "success" && result && <UrlResult result={result} submitted={url}/>} 
    </section>
  </>;
}

function UrlResult({ result, submitted }: { result: UrlAnalysis; submitted: string }) {
  const benign = result.prediction === "benign";
  return <AnalysisResultShell><ResultHeading label={benign ? "Benign" : "Phishing"} context={benign ? "Experimental URL-string classifier output. Benign does not mean safe, verified, or trusted." : "Experimental URL-string classifier output. This is not proof that a website is malicious."} tone={benign ? "neutral" : "caution"}/>
    <div className="submitted-url"><span>Analyzed string</span><code>{submitted}</code></div>
    <div className="result-grid">
      <ResultPanel category="Model output" title="Classifier outputs" tone="model"><ScoreBar label="Benign output" value={result.classifier_outputs.benign}/><ScoreBar label="Phishing output" value={result.classifier_outputs.phish}/><p className="supporting-copy">Classifier outputs are not probabilities of safety, fraud, or harm.</p></ResultPanel>
      <ResultPanel category="Observed indicators" title="Deterministic string observations" tone="observation">{result.observed_indicators.length ? <ul className="indicator-list">{result.observed_indicators.map((item) => <li key={item}>{item}</li>)}</ul> : <div className="no-indicators"><strong>No supported URL-string indicators were detected.</strong><p>This does not establish website safety or legitimacy.</p></div>}</ResultPanel>
    </div>
    {result.disagreement && result.disagreement_message && <InfoCallout title="Signals do not fully agree" tone="warning"><p>{result.disagreement_message}</p><p>The classifier output and observations remain separate; neither has been converted into a combined verdict.</p></InfoCallout>}
    <ResultPanel category="Verification" title="What you can do next" tone="guidance"><NumberedList items={result.verification_guidance}/></ResultPanel>
    <ScopeDetails summary="Limitations and evaluation scope"><ul className="limitation-list">{result.limitations.map((item) => <li key={item}>{item}</li>)}<li>External generalization has not been established by the verified product artifacts.</li></ul></ScopeDetails>
  </AnalysisResultShell>;
}
