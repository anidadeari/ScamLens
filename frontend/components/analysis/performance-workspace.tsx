"use client";

import { useEffect, useState } from "react";
import { ResultError } from "@/components/analysis/result-ui";
import { InfoCallout, PageHeader, StatePanel } from "@/components/ui";
import { getPerformance, normalizeApiError, type ExperimentMetrics, type PerformanceReport } from "@/lib/api";

type State = "loading" | "error" | "success";

const context = {
  message: {
    short: "Message / SMS",
    title: "Message / SMS spam–ham experiment",
    description: "A held-out evaluation of the experimental English SMS spam/ham baseline.",
    scope: "This is not a phishing, fraud, or general safety detector. Ham means non-spam within this task; it does not mean safe.",
  },
  email: {
    short: "Email",
    title: "Email three-class experiment",
    description: "An exploratory Valid, Spam, and Phishing email classification evaluation within its source corpus.",
    scope: "The evaluation is within-corpus only. Real-world, source-independent, and user-independent generalization is not established.",
  },
  url: {
    short: "URL",
    title: "URL phishing–benign experiment",
    description: "A filtered official temporal test of the experimental URL-string-only classifier.",
    scope: "Only URL characters are model inputs. No website content, redirects, DNS, WHOIS, reputation, ownership, certificates, or submitted URL fetching are evaluated.",
  },
} as const;

const metricDefinitions = [
  ["Accuracy", "The share of evaluated examples classified correctly. It can look strong when classes are uneven."],
  ["Macro-F1", "The average F1 score across classes, giving each class equal weight regardless of its size."],
  ["Target recall", "The share of examples in the named target class that the experiment identified correctly."],
] as const;

const evaluationScopeLabels: Record<string, string> = {
  held_out_sms_test_split: "Held-out SMS test split",
  within_corpus_only: "Within-corpus evaluation",
  filtered_official_temporal_test: "Filtered official temporal test",
};

export function PerformanceWorkspace() {
  const [state, setState] = useState<State>("loading");
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [error, setError] = useState<{ title: string; message: string } | null>(null);

  useEffect(() => {
    let active = true;
    getPerformance().then((value) => { if (active) { setReport(value); setState("success"); } })
      .catch((caught) => { if (!active) return; const value = normalizeApiError(caught); setError({ title: value.kind === "unavailable" ? "Performance results unavailable" : "Performance results could not be loaded", message: value.message }); setState("error"); });
    return () => { active = false; };
  }, []);

  return <>
    <PageHeader eyebrow="Evaluation / Stored results" title="Model Performance" description="Read-only experimental evaluation results loaded from existing ScamLens artifacts through the ScamLens API."/>
    <InfoCallout title="Different tasks—not a leaderboard" tone="warning"><p>Message, Email, and URL solve different classification tasks and use different evaluation designs. Their metrics are not directly comparable and must not be used to rank the models.</p></InfoCallout>
    {state === "loading" && <div className="performance-state"><StatePanel tone="loading" title="Loading stored results" description="The ScamLens API is reading existing evaluation artifacts. No submitted user content is sent."/></div>}
    {state === "error" && error && <div className="performance-state"><ResultError title={error.title} message={error.message}/></div>}
    {state === "success" && report && <PerformanceReportView report={report}/>} 
  </>;
}

function PerformanceReportView({ report }: { report: PerformanceReport }) {
  const items = (["message", "email", "url"] as const);
  return <div className="performance-dashboard">
    <nav aria-label="Performance experiments" className="experiment-nav">{items.map((key) => <a href={`#experiment-${key}`} key={key}><span>{context[key].short}</span><small>Separate evaluation</small></a>)}</nav>
    <p className="stored-source"><span aria-hidden="true">◇</span> Source: stored artifacts · read-only API response · no user-submitted content</p>
    <section aria-labelledby="metric-definitions-title" className="metric-definitions"><div><p className="panel-step">How to read the values</p><h2 id="metric-definitions-title">Metric definitions</h2></div><dl>{metricDefinitions.map(([term, description]) => <div key={term}><dt>{term}</dt><dd>{description}</dd></div>)}</dl></section>
    {items.map((key, index) => <ExperimentSection key={key} id={key} index={index + 1} metrics={report[key]}/>) }
    <section aria-labelledby="unavailable-metrics-title" className="performance-availability"><p className="panel-step">Evidence boundary</p><h2 id="unavailable-metrics-title">Metrics not exposed by this API</h2><p>Precision, weighted-F1, sample support, thresholds, confusion matrices, dummy baselines, and detailed temporal/domain/source diagnostics are unavailable in this response. ScamLens does not infer or recompute them in the browser.</p></section>
  </div>;
}

function ExperimentSection({ id, index, metrics }: { id: keyof typeof context; index: number; metrics: ExperimentMetrics }) {
  const copy = context[id];
  return <section aria-labelledby={`experiment-${id}-title`} className={`experiment-section experiment-${id}`} id={`experiment-${id}`}>
    <header className="experiment-header"><div><p className="panel-step">Experiment {String(index).padStart(2, "0")}</p><h2 id={`experiment-${id}-title`}>{copy.title}</h2><p>{copy.description}</p></div><span className="scope-chip">{scopeLabel(metrics.evaluation_scope)}</span></header>
    <div className="performance-metrics" aria-label={`${copy.short} returned metrics`}>
      <Metric interpretation="Correct classifications in this evaluation" label="Accuracy" value={metrics.accuracy}/><Metric interpretation="Equal weight across evaluated classes" label="Macro-F1" value={metrics.macro_f1}/><Metric interpretation={`Identified ${metrics.target_recall_label} examples`} label={`${metrics.target_recall_label} recall`} value={metrics.target_recall}/>
    </div>
    <div className="experiment-detail-grid"><section className="result-card"><p className="panel-step">Evaluation context</p><h3>{metrics.experiment}</h3><dl className="context-list"><div><dt>Evaluation scope</dt><dd className="scope-value"><span>{scopeLabel(metrics.evaluation_scope)}</span><code>{metrics.evaluation_scope}</code></dd></div><div><dt>API source</dt><dd>Stored evaluation artifacts</dd></div></dl></section><section className="result-card"><p className="panel-step">Interpretation & limitations</p><h3>Keep the evidence in scope</h3><p className="scope-copy">{copy.scope}</p><ul className="limitation-list">{metrics.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section></div>
  </section>;
}

function Metric({ label, value, interpretation }: { label: string; value: number; interpretation: string }) {
  const percentage = value * 100;
  return <article className="performance-metric"><span>{label}</span><strong>{value.toFixed(4)}</strong><p>{percentage.toFixed(2)}%</p><small>{interpretation}</small><div aria-label={`${label}: ${value.toFixed(4)}`} aria-valuemax={1} aria-valuemin={0} aria-valuenow={value} className="performance-track" role="meter"><i style={{ width: `${Math.max(0, Math.min(100, percentage))}%` }}/></div></article>;
}

function scopeLabel(value: string) {
  return evaluationScopeLabels[value] ?? value.replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}
