"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark } from "@/components/brand-mark";
import { NavIcon } from "@/components/icons";
import { navigationGroups, utilityNavigation, type NavigationItem } from "@/lib/navigation";

function NavList({ ariaLabel, items }: { ariaLabel: string; items: NavigationItem[] }) {
  const pathname = usePathname();
  return (
    <nav aria-label={ariaLabel}>
      <ul className="nav-list">
        {items.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname === item.href;
          return (
            <li key={item.href}>
              <Link aria-current={active ? "page" : undefined} className="nav-link" href={item.href}>
                <NavIcon name={item.icon} /><span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function NavigationGroups() {
  return <div className="navigation-groups">{navigationGroups.map((group) => <div className="navigation-group" key={group.ariaLabel}>{group.label && <p className="sidebar-label">{group.label}</p>}<NavList ariaLabel={group.ariaLabel} items={group.items}/></div>)}</div>;
}

function Identity() {
  return <Link aria-label="ScamLens overview" className="identity" href="/"><BrandMark/><span><strong>ScamLens</strong><small>Evidence workspace</small></span></Link>;
}

export function Sidebar() {
  return (
    <>
      <aside className="sidebar">
        <Identity />
        <NavigationGroups />
        <div className="sidebar-spacer" />
        <NavList ariaLabel="Supporting navigation" items={utilityNavigation} />
        <p className="sidebar-note">Experimental models<br/>No safety guarantees</p>
      </aside>
      <header className="mobile-header">
        <Identity />
        <details className="mobile-menu">
          <summary aria-label="Open navigation">Menu</summary>
          <div className="mobile-menu-panel"><NavigationGroups/><NavList ariaLabel="Supporting navigation" items={utilityNavigation}/></div>
        </details>
      </header>
    </>
  );
}
