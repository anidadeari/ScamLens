import type { Metadata } from "next";
import { AppShell } from "@/components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "ScamLens — Evidence workspace", template: "%s · ScamLens" },
  description: "Evidence-driven analysis for suspicious digital content.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html data-scroll-behavior="smooth" lang="en"><body><AppShell>{children}</AppShell></body></html>;
}
