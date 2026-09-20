import { StatusBadge } from "@/components/status-badge";

export function AnalysisResultShell({ children }: { children: React.ReactNode }) {
  return <div className="analysis-result">{children}</div>;
}

export function ResultPanel({ category, title, children, tone = "neutral", className = "" }: { category: string; title: string; children: React.ReactNode; tone?: "neutral" | "model" | "observation" | "limitation" | "guidance"; className?: string }) {
  return <section className={`result-card result-panel result-panel-${tone} ${className}`.trim()}><p className="panel-step">{category}</p><h3>{title}</h3>{children}</section>;
}

export function ScopeDetails({ summary, children }: { summary: string; children: React.ReactNode }) {
  return <details className="scope-details"><summary>{summary}</summary><div>{children}</div></details>;
}

export function ScoreBar({ label, value, marker, markerLabel }: { label: string; value: number; marker?: number; markerLabel?: string }) {
  const bounded = Math.max(0, Math.min(1, value));
  const markerPosition = marker === undefined ? undefined : Math.max(0, Math.min(1, marker));
  return <div className="score-row"><div className="score-label"><span>{label}</span><strong>{value.toFixed(3)}</strong></div><div aria-label={`${label}: ${value.toFixed(3)}`} aria-valuemax={1} aria-valuemin={0} aria-valuenow={value} className="score-track" role="meter"><span className="score-fill" style={{ width: `${bounded * 100}%` }}/>{markerPosition !== undefined && <span aria-hidden="true" className="score-marker" style={{ left: `${markerPosition * 100}%` }}/>}</div>{markerLabel && <small className="score-note">{markerLabel}</small>}</div>;
}

export function ResultHeading({ label, context, tone = "neutral" }: { label: string; context: string; tone?: "neutral" | "caution" }) {
  return <div className={`result-heading result-${tone}`}><div><p className="result-kicker">Model assessment</p><h2>{label}</h2><p>{context}</p></div><StatusBadge tone={tone === "caution" ? "caution" : "neutral"}>Model output</StatusBadge></div>;
}

export function NumberedList({ items }: { items: string[] }) {
  return <ol className="guidance-list">{items.map((item, index) => <li key={`${index}-${item}`}><span>{String(index + 1).padStart(2, "0")}</span><p>{item}</p></li>)}</ol>;
}

export function ResultError({ title, message, id }: { title: string; message: string; id?: string }) {
  return <div aria-live="assertive" className="analysis-error" id={id} role="alert"><span aria-hidden="true">!</span><div><strong>{title}</strong><p>{message}</p></div></div>;
}
