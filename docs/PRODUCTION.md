# Production-readiness architecture

This document defines provider-neutral controls and deployment gates. It does
not approve a public deployment. Provider-specific validation, licensing
review, and controlled load testing remain required.

## A. Local development

Run FastAPI and Next.js separately over loopback HTTP:

```bash
.venv/bin/python -m uvicorn scamlens.api.app:app --host 127.0.0.1 --port 8000
cd frontend
npm run dev
```

The backend permits only `http://localhost:3000` and
`http://127.0.0.1:3000` by default. Forwarding headers are ignored. These
defaults are intentionally suitable for local development, not public access.

## B. Production topology

```text
Browser
  | HTTPS only
  v
Public ingress / reverse proxy (TLS, redirects, body and infrastructure limits)
  |-------------------- / --------------------> private Next.js process
  `-------------------- /api/* ----------------> private FastAPI process
                                                   | local filesystem/process
                                                   +--> model artifacts
                                                   `--> local Tesseract
```

Only the ingress is public. Next.js, FastAPI, artifacts, and Tesseract should
remain on private interfaces. Same-origin routing is preferred: `/` reaches
Next.js and `/api/*` reaches FastAPI. Browser requests then use relative API
paths, and CORS is not needed for ordinary application traffic.

The ingress terminates TLS, redirects HTTP to HTTPS, applies the final browser
security-header policy, rejects oversized bodies before ASGI, and enforces
shared rate limits. Backend-to-local-artifact and backend-to-Tesseract work is
local and must not perform external requests.

## C. Environment configuration

Backend settings are loaded centrally by `scamlens.api.config`. Invalid
security-sensitive values stop application startup. Environment variables:

| Variable | Development default | Production rule |
| --- | --- | --- |
| `SCAMLENS_ENV` | `development` | Set to `production` |
| `SCAMLENS_PUBLIC_ORIGIN` | not required | Required, exact HTTPS origin |
| `SCAMLENS_CORS_ORIGINS` | two localhost origins | Optional comma-separated exact HTTPS origins; never `*` |
| `SCAMLENS_TRUST_FORWARDED_HEADERS` | `false` | Must remain false until trusted proxy networks and chain semantics are deployment-configured |
| `SCAMLENS_INFERENCE_REQUESTS_PER_MINUTE` | `60` | Positive integer; tune with evidence |
| `SCAMLENS_OCR_REQUESTS_PER_MINUTE` | `10` | Positive integer; keep stricter than cheap routes |
| `SCAMLENS_PERFORMANCE_REQUESTS_PER_MINUTE` | `120` | Positive integer |
| `SCAMLENS_OCR_CONCURRENCY_LIMIT` | `2` | Positive integer; load-test before changing |
| `SCAMLENS_OCR_TIMEOUT_SECONDS` | `15` | Positive integer; Tesseract execution timeout |

Message (5,000 characters), email (100,000 combined characters), URL (2,048
characters), upload (5 MiB), and decoded-image (20 MP) limits remain fixed
application contracts rather than deployment knobs. The example environment
files contain placeholders and no secrets.

For same-origin production builds, set `NEXT_PUBLIC_SCAMLENS_ENV=production`
and leave `NEXT_PUBLIC_SCAMLENS_API_BASE_URL` unset or empty. If a separate API
origin is unavoidable, it must be HTTPS and must also appear in validated
backend CORS configuration. `NEXT_PUBLIC_*` values are browser-visible and
must never contain secrets.

## D. Build and start commands

Build and run Next.js without its development server:

```bash
cd frontend
NEXT_PUBLIC_SCAMLENS_ENV=production NEXT_PUBLIC_SCAMLENS_API_BASE_URL= npm ci
NEXT_PUBLIC_SCAMLENS_ENV=production NEXT_PUBLIC_SCAMLENS_API_BASE_URL= npm run build
NEXT_PUBLIC_SCAMLENS_ENV=production NEXT_PUBLIC_SCAMLENS_API_BASE_URL= npm run start -- --hostname 127.0.0.1 --port 3000
```

Start FastAPI without reload and bind it only to the private/loopback interface
selected by the deployment:

```bash
SCAMLENS_ENV=production \
SCAMLENS_PUBLIC_ORIGIN=https://replace-with-real-origin.example \
.venv/bin/python -m uvicorn scamlens.api.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-server-header
```

The example hostname is a placeholder. Environment injection belongs to the
eventual process/container platform. Do not commit real deployment values.

## E. Ingress responsibilities

The ingress must enforce a hard request-body limit before proxying bytes to
ASGI. Configure it only slightly above 5 MiB so normal multipart framing fits
while the application payload limit remains exactly 5 MiB. The exact overhead
margin must be verified against the chosen ingress and client implementation.

These are distinct boundaries:

1. ingress body limit: rejects the whole HTTP request before ASGI;
2. application upload limit: reads at most 5 MiB plus one byte and validates the actual uploaded file size;
3. decoded image limit: rejects images above 20 megapixels and unsafe/corrupt/mismatched formats.

No FastAPI middleware can honestly replace the first boundary. The ingress
must also apply shared rate limits before expensive work, with tighter OCR
limits and appropriate exemptions or separate policy for liveness/readiness.
The Python limiter remains defense in depth.

## F. HTTPS and security headers

Production browser traffic must be HTTPS-only. TLS termination and
HTTP-to-HTTPS redirects belong at the trusted ingress so submitted content is
not sent over plaintext. HSTS is intentionally not emitted by the applications:
enable it at ingress only after the real HTTPS deployment, domain coverage,
and rollback implications have been validated.

The production backend and the frontend emit defense-in-depth `nosniff`,
no-referrer, anti-framing, Permissions-Policy, and limited CSP directives. The frontend CSP constrains
framing, objects, and base URLs without restricting Next.js scripts in a way
that breaks hydration. The API uses a stricter default-deny CSP because it
serves JSON. The final ingress policy must preserve or strengthen these headers
and be tested with the deployed Next.js output.

## G. CORS and trusted proxies

Same-origin routing minimizes CORS. Production refuses to start without an
exact HTTPS public origin and rejects wildcard, path-bearing, credential-bearing,
or malformed origins. Cross-origin support is explicit only.

Rate limiting uses the direct ASGI peer. `X-Forwarded-For`, `Forwarded`, and
similar headers are ignored even when supplied. Enabling trusted forwarding is
deliberately rejected because provider-neutral code cannot know the trusted
proxy addresses, hop count, or header-rewrite guarantees. The eventual ingress
must strip client-supplied forwarding headers and set canonical ones, and the
ASGI server must trust only explicitly configured proxy networks. Until that
deployment-specific work is complete, keep direct-peer behavior and enforce
client-aware limits at ingress.

## H. Health and readiness

- `/api/live`: process liveness only; no dependency work.
- `/api/health`: retained compatibility alias for basic health.
- `/api/ready`: verifies that the three local model bundles can be loaded; it
  performs no inference, OCR, network access, or path disclosure.

These endpoints bypass application rate limiting. An ingress should permit
private orchestrator probes while preventing health routes from becoming an
unbounded public abuse target.

## I. Workers, OCR, and capacity

One FastAPI worker is the correctness-oriented starting point because the
current rate histories and two-slot OCR gate live independently in each
process. This is not a capacity recommendation. Every additional worker loads
its own model copies, creates its own rate-limit state and OCR slots, and can
increase Tesseract subprocess concurrency and CPU/memory pressure. Tesseract is
offloaded from the event loop, but its subprocess remains CPU-intensive.

Multiple workers or horizontal replicas require shared ingress abuse controls.
Worker counts, OCR concurrency, timeouts, memory limits, and process recycling
require controlled load tests on the actual deployment class. Next.js runs as
a separate production process and needs independent CPU/memory supervision.

## J. Privacy and logging

Application code does not intentionally log or persist message text, email
subject/body, screenshots, OCR output, or submitted URL strings. It uses no
cookies, browser storage, analytics, or telemetry. Ordinary server/access logs
may contain HTTP metadata such as client address, path, status, duration, and
user agent. The chosen ingress, runtime, crash reporting, and hosting platform
must be reviewed to ensure bodies, query values, multipart content, and error
locals are not captured. Do not describe this as zero logging.

## K. Packaging and remaining provider work

No container files are added in this milestone. A reproducible image would
need a pinned base OS, Tesseract plus English language data, Python/Node build
stages, non-root runtime ownership, artifact-copy rules, and redistribution
approval for bundled models/data. The unresolved redistribution gate makes a
public image premature; local packaging behavior remains unchanged.

Before deployment, select and validate an ingress implementation, real domain
and certificates, trusted proxy networks, pre-ASGI body syntax, shared rate
limits, access-log policy, secret/config injection, process supervision,
resource limits, backup/rollback policy, vulnerability update process, and
controlled load-test results. See `LICENSING_REVIEW.md` for redistribution
gates.
