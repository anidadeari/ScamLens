import type { NavigationItem } from "@/lib/navigation";

export function NavIcon({ name }: { name: NavigationItem["icon"] }) {
  const paths: Record<NavigationItem["icon"], React.ReactNode> = {
    overview: <><rect height="6" rx="1" width="6" x="3" y="3"/><rect height="6" rx="1" width="6" x="15" y="3"/><rect height="6" rx="1" width="6" x="3" y="15"/><rect height="6" rx="1" width="6" x="15" y="15"/></>,
    message: <path d="M4 5h16v11H9l-5 4V5Zm4 4h8M8 12h5" />,
    email: <><rect height="14" rx="2" width="18" x="3" y="5"/><path d="m4 7 8 6 8-6"/></>,
    screenshot: <><rect height="16" rx="2" width="18" x="3" y="4"/><path d="m7 15 3-3 3 2 3-4 4 5M8 8h.01"/></>,
    url: <><path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1"/><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1"/></>,
    performance: <path d="M4 20V10m5 10V4m6 16v-7m5 7V7" />,
    privacy: <path d="M12 3 20 7v6c0 4.5-3.2 7.2-8 9-4.8-1.8-8-4.5-8-9V7l8-4Zm-3 9 2 2 4-5" />,
  };
  return <svg aria-hidden="true" className="nav-icon" viewBox="0 0 24 24">{paths[name]}</svg>;
}
