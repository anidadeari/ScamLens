import { ApiHealth } from "@/components/api-health";
import { Sidebar } from "@/components/sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <Sidebar />
      <main className="main-content" id="main-content" tabIndex={-1}>
        <div className="top-context"><span>Evidence analysis · explicit limitations</span><ApiHealth /></div>
        {children}
      </main>
    </div>
  );
}
