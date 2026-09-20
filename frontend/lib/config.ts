const configuredBaseUrl = process.env.NEXT_PUBLIC_SCAMLENS_API_BASE_URL?.trim();
const environment = process.env.NEXT_PUBLIC_SCAMLENS_ENV?.trim().toLowerCase() || "development";

if (environment === "production" && configuredBaseUrl && new URL(configuredBaseUrl).protocol !== "https:") {
  throw new Error("Production API origins must use secure transport or same-origin routing.");
}

export const API_BASE_URL = (
  configuredBaseUrl ?? (environment === "production" ? "" : "http://127.0.0.1:8000")
).replace(/\/$/, "");
