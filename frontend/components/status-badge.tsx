type BadgeTone = "neutral" | "accent" | "success" | "caution" | "danger";

export function StatusBadge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: BadgeTone }) {
  return <span className={`status-badge badge-${tone}`}>{children}</span>;
}
