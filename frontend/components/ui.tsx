import Link from "next/link";

export function PageHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: React.ReactNode }) {
  return <header className="page-header"><p className="eyebrow">{eyebrow}</p><div className="page-title-row"><div><h1>{title}</h1><p>{description}</p>{children}</div></div></header>;
}

export function SectionHeader({ eyebrow, title, description, titleId }: { eyebrow?: string; title: string; description?: string; titleId?: string }) {
  return <header className="section-header">{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h2 id={titleId}>{title}</h2>{description && <p>{description}</p>}</header>;
}

export function ActionLink({ children, href }: { children: React.ReactNode; href: string }) {
  return <Link className="button button-primary" href={href}>{children}<span aria-hidden="true">→</span></Link>;
}

export function InfoCallout({ title, children, tone = "info", className = "" }: { title: string; children: React.ReactNode; tone?: "info" | "warning"; className?: string }) {
  return <aside className={`callout callout-${tone} ${className}`.trim()}><strong>{title}</strong><div>{children}</div></aside>;
}

export function AnalysisPanel({ children, label }: { children: React.ReactNode; label: string }) {
  return <section aria-label={label} className="analysis-panel">{children}</section>;
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return <div className="empty-state"><span aria-hidden="true" className="empty-glyph">◇</span><h2>{title}</h2><p>{description}</p><Link className="button button-secondary" href="/">Return to overview</Link></div>;
}

export type StateTone = "empty" | "loading" | "success" | "caution" | "error" | "unavailable";

export function StatePanel({ tone, title, description }: { tone: StateTone; title: string; description: string }) {
  return <div aria-live={tone === "loading" ? "polite" : undefined} className={`state-panel state-${tone}`} role={tone === "error" || tone === "unavailable" ? "alert" : "status"}><span aria-hidden="true" className="state-symbol"/><div><strong>{title}</strong><p>{description}</p></div></div>;
}
