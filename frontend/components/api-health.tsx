"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL } from "@/lib/config";

type HealthState = "loading" | "available" | "unavailable";

export function ApiHealth() {
  const [state, setState] = useState<HealthState>("loading");

  useEffect(() => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 3500);
    fetch(`${API_BASE_URL}/api/health`, { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Health endpoint unavailable");
        const body: unknown = await response.json();
        if (!body || typeof body !== "object" || !("status" in body) || body.status !== "ok") {
          throw new Error("Unexpected health response");
        }
        setState("available");
      })
      .catch(() => setState("unavailable"))
      .finally(() => window.clearTimeout(timeout));
    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, []);

  const copy = {
    loading: ["Checking system", "Connecting to API", "status-dot status-loading"],
    available: ["System ready", "API connected", "status-dot status-available"],
    unavailable: ["API unavailable", "Analysis service not connected", "status-dot status-unavailable"],
  } as const;

  return (
    <div aria-live="polite" className="api-health" data-state={state} role="status">
      <span aria-hidden="true" className={copy[state][2]} />
      <span className="health-copy"><strong>{copy[state][0]}</strong><small>{copy[state][1]}</small></span>
    </div>
  );
}
