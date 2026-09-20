import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

describe("runtime assets", () => {
  it("does not require remote fonts, image CDNs, scripts, or tracking", () => {
    const roots = ["app", "components", "lib"];
    const files = roots.flatMap((root) =>
      fs.readdirSync(path.resolve(root), { recursive: true, encoding: "utf8" })
        .filter((name) => /\.(css|ts|tsx)$/.test(name))
        .map((name) => path.resolve(root, name))
        .filter((name) => fs.statSync(name).isFile())
    );
    const source = files.map((file) => fs.readFileSync(file, "utf8")).join("\n");
    expect(source).not.toMatch(/next\/font|<script|<img|googletagmanager|analytics\.(track|identify)|gtag\s*\(/i);
    expect(source).not.toMatch(/@import\s+url|https:\/\//i);
  });

  it("defines desktop, tablet, mobile, focus, and reduced-motion behavior", () => {
    const css = fs.readFileSync(path.resolve("app/globals.css"), "utf8");
    expect(css).toContain("@media (max-width: 1180px)");
    expect(css).toContain("@media (max-width: 1280px)");
    expect(css).toContain("@media (max-width: 820px)");
    expect(css).toContain("@media (max-width: 580px)");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
    expect(css).toContain(":focus-visible");
    expect(css).toContain("overflow-x: hidden");
  });
});
