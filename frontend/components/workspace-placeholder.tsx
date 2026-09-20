import { StatusBadge } from "@/components/status-badge";
import { EmptyState, InfoCallout, PageHeader } from "@/components/ui";

export function WorkspacePlaceholder({ eyebrow, title, description, badge, disclosure }: { eyebrow: string; title: string; description: string; badge: string; disclosure: string }) {
  return <><PageHeader eyebrow={eyebrow} title={title} description={description}/><div className="workspace-meta"><StatusBadge tone="neutral">{badge}</StatusBadge><span>Frontend foundation · Milestone 15</span></div><InfoCallout title="Current scope"><p>{disclosure}</p></InfoCallout><EmptyState title="Analysis workspace coming in the next integration milestone" description="This polished route shell is intentionally not connected to analysis endpoints yet. The existing Streamlit workflow remains available."/></>;
}
