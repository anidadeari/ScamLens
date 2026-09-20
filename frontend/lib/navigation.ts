export type NavigationItem = {
  label: string;
  href: string;
  icon: "overview" | "message" | "email" | "screenshot" | "url" | "performance" | "privacy";
};

export type NavigationGroup = { label: string; ariaLabel: string; items: NavigationItem[] };

export const overviewNavigation: NavigationItem[] = [
  { label: "Overview", href: "/", icon: "overview" },
];

export const analysisNavigation: NavigationItem[] = [
  { label: "Message", href: "/message", icon: "message" },
  { label: "Email", href: "/email", icon: "email" },
  { label: "Screenshot", href: "/screenshot", icon: "screenshot" },
  { label: "URL", href: "/url", icon: "url" },
];

export const transparencyNavigation: NavigationItem[] = [
  { label: "Model Performance", href: "/performance", icon: "performance" },
];

export const navigationGroups: NavigationGroup[] = [
  { label: "", ariaLabel: "Overview navigation", items: overviewNavigation },
  { label: "Analyze", ariaLabel: "Analysis navigation", items: analysisNavigation },
  { label: "Transparency", ariaLabel: "Transparency navigation", items: transparencyNavigation },
];

export const primaryNavigation = navigationGroups.flatMap((group) => group.items);

export const utilityNavigation: NavigationItem[] = [
  { label: "Privacy & approach", href: "/#scope", icon: "privacy" }
];
