# ScamLens

ScamLens provides separate local experimental analyses for English SMS,
three-class email, URL strings, and user-reviewed screenshot OCR text, plus a
stored Model Performance view.

The modes are independent and none is a safety guarantee. URL Analysis never
visits a submitted address: it parses the literal string and runs a local
character-ngram model only. It performs no HTTP, DNS, WHOIS, certificate,
domain-age, ownership, or reputation lookup.

## Clean-clone setup

The current development baseline is verified with Python 3.12.3, Node.js
22.23.2, npm 10.9.8, and Tesseract 5.3.4 with English language data. Other
versions have not been validated by this repository's current quality gate.

Install Tesseract and its English language data using the appropriate system
package manager. Then, from the project root, create the Python environment and
install the pinned Python dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Install the locked frontend dependencies separately:

```bash
cd frontend
npm ci
cd ..
```

### Source-only clone limitation

Datasets and the complete `artifacts/` tree are intentionally excluded from
version control while redistribution and publication rights remain under
review. A source-only clone therefore does not contain the trained models or
stored metric artifacts. Analysis endpoints, model-backed interfaces, and API
readiness checks that require those files will not work until authorized
artifacts are supplied locally or legally regenerated from appropriately
obtained source data. This repository does not provide or imply an authorized
download route for those datasets or models.

The repository source and documentation do not grant rights to any underlying
dataset, trained model, corpus record, or derived artifact. Review
[`docs/LICENSING_REVIEW.md`](docs/LICENSING_REVIEW.md),
[`dataset provenance`](docs/DATASET_PROVENANCE.md), and
[`model provenance`](docs/MODEL_PROVENANCE.md) before any distribution or
publication decision.

## Run locally

The existing virtual environment does not currently include the optional shell
activation script. Use its Python interpreter directly:

```bash
.venv/bin/python -m streamlit run app.py
```

Streamlit prints a local URL, normally `http://localhost:8501`. Open that URL in
your browser. Stop the development server with `Ctrl+C`.

### Local API

Start the FastAPI development server from the project root:

```bash
.venv/bin/python -m uvicorn scamlens.api.app:app --host 127.0.0.1 --port 8000
```

The local OpenAPI documentation is then available at
`http://127.0.0.1:8000/docs`. This milestone does not expose or deploy the API
publicly. Its stable application routes are:

- `GET /api/health`
- `POST /api/analyze/message` with JSON `{"text": "..."}`
- `POST /api/analyze/email` with JSON `{"subject": "...", "body": "..."}`
- `POST /api/analyze/url` with JSON `{"url": "https://..."}`
- `POST /api/ocr` with one multipart file field named `file`
- `GET /api/performance`

Message, email, and URL routes delegate to the existing local inference and
observation modules. The OCR route returns extracted English text for review
and never classifies it. A client must submit reviewed text separately to the
message route after an explicit user action.

Browser access is limited to the explicitly configured development origins
`http://localhost:3000` and `http://127.0.0.1:3000`; wildcard CORS is not used.
These origins must be reviewed and tightened for any future deployment.

## Input policy

Each mode validates its own input and loads only its corresponding trusted
local artifact; users cannot upload model files. URL input must include an
explicit `http://` or `https://` scheme, may be at most 2,048 characters, and
is rejected rather than silently rewritten when malformed.

## Screenshot OCR

Screenshot Analysis accepts PNG, JPEG/JPG, and WEBP files up to 5 MiB and 20
decoded megapixels. Pillow validates the actual image format and decoding.
Tesseract 5 with English language data performs OCR locally through pinned
`pytesseract`. No image preprocessing is currently applied because an
improvement has not been demonstrated for the supported screenshot population.

OCR text is always displayed in an editable field. It is never classified
until the user reviews it and explicitly chooses **Analyze as Message** or
**Analyze as Email**. Those actions delegate to the corresponding existing
experimental pipeline; they do not create a screenshot model or establish
phishing, fraud, authenticity, or safety. Images and OCR text are not written
to files or sent to an external service. URLs and QR codes in screenshots are
not opened.

Submitted text is used only for local inference. The application does not write
messages to files, intentionally log them, or send them to external services.
Standard infrastructure outside this prototype may have its own logging, so a
future deployment requires a separate privacy and operations review.

The FastAPI application does not intentionally log request bodies, submitted
text or URLs, screenshots, or OCR output. Uvicorn's default access log can
record request metadata such as method, path, status, client address, and
timing, but not request bodies. Reverse proxies, hosting platforms, operating
systems, and custom server configuration remain outside the application's
control; this is not an absolute privacy guarantee.

### Development request safeguards

The API applies process-local in-memory rate limits using only the direct ASGI
connection peer as client identity. It deliberately ignores forwarding headers
because trusted-proxy behavior has not been configured. OCR has a lower request
limit than text inference and a fail-fast two-execution concurrency gate; its
blocking Tesseract call is offloaded from the event loop and retains the
existing 15-second engine timeout. The default concurrency value is a
conservative development setting, not a production capacity claim; tune it
only with controlled load testing.

These controls reset on process restart and are independent in every worker.
They therefore do not provide aggregate protection for multiple workers or
hosts. A production reverse proxy or shared enforcement layer must impose a
true pre-ASGI request-body limit and coordinated rate/concurrency policy. The
application's 5 MiB screenshot check happens after multipart handling has begun
and cannot honestly replace that infrastructure boundary.

Provider-neutral production-readiness architecture, configuration, ingress,
HTTPS, health/readiness, worker, and logging requirements are documented in
[`docs/PRODUCTION.md`](docs/PRODUCTION.md). The repository-only redistribution
inventory and unresolved gates are in
[`docs/LICENSING_REVIEW.md`](docs/LICENSING_REVIEW.md), with detailed
[`dataset provenance`](docs/DATASET_PROVENANCE.md),
[`model provenance`](docs/MODEL_PROVENANCE.md), and
[`third-party notices`](docs/THIRD_PARTY_NOTICES.md). These controls do not
constitute approval for public deployment. Datasets and trained model artifacts
remain intentionally excluded from version control; publication and
redistribution rights remain under review, and publication of this source must
not be interpreted as granting rights to the underlying datasets or models.

## Tests

```bash
.venv/bin/pytest -q
cd frontend
npm test
npm run test:e2e
npm run lint
npm run typecheck
npm run build
```

The browser suite uses Playwright with an already installed Google Chrome. It
starts a loopback-only Next.js test server, intercepts the configured ScamLens
API with deterministic synthetic responses, and does not contact submitted URL
destinations. Browser binaries are not installed by the test command.

Dataset provenance, licensing, split methodology, model selection, metrics,
and limitations are documented in `docs/DATASETS.md` and the model cards under
the artifact directories.

## Next.js frontend

The frontend under `frontend/` provides the Overview, Message, Email,
Screenshot, URL, and Model Performance routes. It calls the configured
ScamLens API for explicit analyses and health status. Streamlit remains
available independently for the legacy local interface.

Copy `frontend/.env.example` to `frontend/.env.local` if the local FastAPI URL
needs to be changed. Then start the API and frontend in separate terminals:

```bash
.venv/bin/python -m uvicorn scamlens.api.app:app --host 127.0.0.1 --port 8000
cd frontend
npm run dev
```

Open `http://localhost:3000`. The frontend contains no remote fonts, image
assets, analytics, tracking, or third-party runtime scripts.
