import { afterEach, describe, expect, it, vi } from "vitest";

const originalEnvironment = process.env.NEXT_PUBLIC_SCAMLENS_ENV;
const originalBase = process.env.NEXT_PUBLIC_SCAMLENS_API_BASE_URL;

afterEach(() => {
  if (originalEnvironment === undefined) delete process.env.NEXT_PUBLIC_SCAMLENS_ENV;
  else process.env.NEXT_PUBLIC_SCAMLENS_ENV = originalEnvironment;
  if (originalBase === undefined) delete process.env.NEXT_PUBLIC_SCAMLENS_API_BASE_URL;
  else process.env.NEXT_PUBLIC_SCAMLENS_API_BASE_URL = originalBase;
  vi.resetModules();
});

describe("frontend runtime configuration", () => {
  it("defaults production to same-origin API routing", async () => {
    process.env.NEXT_PUBLIC_SCAMLENS_ENV = "production";
    delete process.env.NEXT_PUBLIC_SCAMLENS_API_BASE_URL;
    vi.resetModules();
    const config = await import("@/lib/config");
    expect(config.API_BASE_URL).toBe("");
  });

  it("rejects an insecure separate production API origin", async () => {
    process.env.NEXT_PUBLIC_SCAMLENS_ENV = "production";
    process.env.NEXT_PUBLIC_SCAMLENS_API_BASE_URL = "http://api.example.invalid";
    vi.resetModules();
    await expect(import("@/lib/config")).rejects.toThrow(/secure transport/i);
  });
});
