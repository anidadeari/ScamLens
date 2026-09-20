import { expect, test } from "@playwright/test";
import { json, mockHealth, performanceResult } from "./fixtures";

const viewports = [
  { width: 1440, height: 900 }, { width: 1280, height: 800 },
  { width: 768, height: 1024 }, { width: 390, height: 844 },
];

for (const viewport of viewports) {
  test(`all routes avoid horizontal overflow and clipping at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport); await mockHealth(page);
    await page.route("**/api/performance", (route) => json(route, performanceResult));
    for (const path of ["/", "/message", "/email", "/screenshot", "/url", "/performance"]) {
      await page.goto(path);
      const dimensions = await page.evaluate(() => ({ documentWidth: document.documentElement.scrollWidth, viewportWidth: document.documentElement.clientWidth }));
      expect(dimensions.documentWidth, `${path} overflowed`).toBeLessThanOrEqual(dimensions.viewportWidth);
      await expect(page.locator("main")).toBeVisible();
    }
  });
}

test("keyboard navigation exposes visible focus and reaches main content", async ({ page }) => {
  await mockHealth(page); await page.goto("/message");
  await page.keyboard.press("Tab"); await expect(page.locator(".skip-link")).toBeFocused();
  await page.keyboard.press("Enter"); await expect(page.locator("#main-content")).toBeFocused();
  await page.keyboard.press("Tab");
  const focusStyle = await page.evaluate(() => { const element = document.activeElement as HTMLElement; const style = getComputedStyle(element); return { tag: element.tagName, outline: style.outlineStyle, width: style.outlineWidth }; });
  expect(focusStyle.tag).not.toBe("BODY"); expect(focusStyle.outline === "none" && focusStyle.width === "0px").toBe(false);
});

test("reduced motion disables nonessential transitions", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" }); await mockHealth(page); await page.goto("/");
  const durations = await page.evaluate(() => [...document.querySelectorAll("*")].flatMap((node) => getComputedStyle(node).transitionDuration.split(",").map(parseFloat)));
  expect(Math.max(...durations)).toBeLessThanOrEqual(0.001);
});
