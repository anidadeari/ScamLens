# ScamLens UX Architecture

This document maps the actual ScamLens routes, workflows, and evidence hierarchy introduced in Milestone 23.

## Product hierarchy

ScamLens has three navigation levels:

1. **Overview** — explains the product, offers the four analysis entry points, shows the factual workflow, states trust/privacy boundaries, and links to methodology.
2. **Analyze** — Message, Email, Screenshot, and URL workspaces.
3. **Transparency** — Model Performance, a read-only view of stored evaluation results.

Desktop presents this hierarchy in a stable sidebar. At 820 px and below, the same links and group labels appear in an accessible native disclosure menu. Route names stay concise; page headings provide the expanded analysis names.

No additional routes are used to imply product breadth. Privacy and approach is an anchored section on Overview rather than a decorative standalone page.

## Shared analysis-page structure

Each analysis route follows a common hierarchy while retaining modality-specific controls:

1. Page header: modality, concise purpose, and visible experimental scope where needed.
2. Input workspace: labeled content field or file input, constraints, handling note, and explicit primary action.
3. Scope panel: what the modality checks and what it cannot establish.
4. Process state: intentional empty state, named loading state, or actionable sanitized error.
5. Result workspace: assessment, exact model signals, observations where supported, limitations, and verification guidance.

The browser invalidates displayed results when their owning input changes. Request-generation checks prevent late responses from restoring stale results. Duplicate submission is disabled during processing.

## Message workflow

The user pastes up to 5,000 characters of English SMS-style content and selects **Analyze message**. The configured API returns Spam or Ham (non-spam), a spam classifier score, the configured threshold, and limitations.

The result first states the model assessment and a critical interpretation. A Ham output explicitly says it does not confirm safety, authenticity, or trustworthiness. A Spam output is presented as spam-like classifier evidence, not proof of fraud. The exact score and threshold remain inspectable and are described as classifier outputs rather than probabilities.

## Email workflow

The user enters a subject, body, or both, within the existing 100,000-character combined limit, then selects **Analyze email**. Experimental and within-corpus scope is visible at the page heading.

The result order is:

1. Valid, Spam, or Phishing model assessment and critical interpretation.
2. Three exact classifier outputs.
3. Deterministic textual observations, kept separate from the model.
4. Model/observation disagreement when returned by the API.
5. Verification guidance.
6. Expandable experiment scope and additional limitations.

There is no synthetic risk score. A Valid output is neutral and never becomes a Safe state.

## Screenshot workflow

Screenshot Analysis is an explicit five-stage progression:

1. **Upload** — select or drag a PNG, JPEG/JPG, or WEBP image within the 5 MiB and 20-megapixel constraints. The UI shows filename, size, local preview, and removal control.
2. **OCR** — select **Extract text**. The configured ScamLens backend runs Tesseract OCR. There is no fake percentage and no classification at this stage.
3. **Review** — inspect and edit the extracted text. The interface warns that OCR may omit, substitute, merge, or invent characters.
4. **Choose type** — explicitly select Message or Email analysis. ScamLens does not infer the content type.
5. **Result** — show **Analyzed as Message** or **Analyzed as Email**, then reuse the corresponding result presentation. The context label records the user's explicit mode selection; it is not a classifier output.

For Email, the reviewed text is sent as the body and the subject remains blank. Changing the file, rerunning OCR, changing reviewed text, or switching analysis type invalidates incompatible state. OCR output is never represented as authoritative or infallible.

## URL workflow

The user enters an HTTP or HTTPS URL string up to 2,048 characters and selects **Analyze URL**. Before input, the UI explains that ScamLens analyzes characters and structure without visiting the address.

The submitted URL is rendered as inert code text, not a link. No website content, redirects, favicon, preview, DNS, WHOIS, reputation, ownership, or certificate check is performed. Results preserve Benign/Phishing classifier semantics, keep deterministic string observations separate, and show disagreement when returned. Benign is not verified legitimacy; Phishing is not proof of malicious ownership.

## Model Performance workflow

Model Performance calls only `/api/performance` and renders the stored Message, Email, and URL experiment outputs. The page states that the tasks and evaluation designs are not directly comparable. Each experiment includes its name, evaluation scope, accuracy, macro-F1, target-recall label/value, and returned limitations.

Primary scope chips translate the exact API values into conservative labels: **Held-out SMS test split**, **Within-corpus evaluation**, and **Filtered official temporal test**. The raw identifiers remain visible in evaluation-context details. Presentation changes do not modify or reinterpret the API values.

Accuracy, macro-F1, and target recall have visible plain-language definitions. The UI does not infer absent metrics, average experiments, rank models, or create an overall ScamLens accuracy.

## Result evidence hierarchy

Every result category answers a different question:

| Category | Question | Source and treatment |
| --- | --- | --- |
| Model output | What did the trained classifier return? | Exact API class and scores, labeled experimental where relevant |
| Observation | What supported deterministic pattern was present? | API-provided text/URL observations, visually separate from prediction |
| Limitation | What can this evidence not establish? | Critical language near the assessment; details remain expandable |
| Verification | What can the user independently do next? | Existing API/product-approved guidance, shown as ordered actions |

Disagreement is a relationship between model output and observations, not a combined verdict. The interface never converts evidence into Low/Medium/High risk.

## Empty, loading, and error states

Empty states name the next action: paste a message, enter email content, upload a screenshot, or enter a URL. Loading states name the actual process and never show invented progress. Error alerts distinguish validation, service availability, file constraints, OCR issues, and malformed responses using sanitized copy. They do not reveal stack traces, internal paths, or raw transport errors.

The low-key API status in the shell uses deployment-neutral wording and reports only availability. Input-handling notes likewise state that content reaches the configured ScamLens API without claiming it stays on the device. Status does not claim protection, threat-feed activity, or security coverage.

## Readability and density

Material caveats—including limitations, field hints, observation explanations, verification steps, scope statements, and metric interpretations—must remain readable at laptop viewing distance. Tertiary styling is reserved for subordinate metadata. Result cards and context panels size intrinsically and align at the top, so a short neighboring card does not acquire an empty lower half. The Overview hero, experiment spacing, and analysis workspaces use tighter vertical rhythm at laptop widths while preserving clear grouping and readable line lengths.

## Accessibility considerations

- A skip link targets the main content.
- Navigation has distinct landmarks, visible group labels, current-page state, and a native mobile disclosure.
- All inputs have programmatic labels; relevant helper/privacy text is connected to the input.
- Async regions announce status changes, and loading regions expose busy state.
- Result scores are semantic meters with exact textual values.
- Screenshot stages are an ordered list with a current-step marker.
- File selection has a keyboard-operable fallback to drag and drop.
- Buttons and links match their actual behavior and keep 44 px touch targets.
- Focus rings are visible, focus order follows document order, and reduced motion is respected.

The interface does not introduce modals or custom widgets that require additional keyboard contracts. Manual assistive-technology review remains advisable before public release.

## Explicit non-goals

This UX does not provide or imply:

- definitive fraud, phishing, authenticity, or safety verification;
- URL navigation, fetching, content inspection, reputation, DNS, WHOIS, ownership, or certificate validation;
- real-time threat intelligence, attack blocking, monitoring, protection counts, or live security telemetry;
- automatic classification after OCR or automatic Message/Email selection;
- perfect OCR or image-authenticity analysis;
- cross-model ranking, aggregate accuracy, invented metrics, or calibrated probabilities;
- accounts, cookies, analytics, telemetry, tracking, persistence, or a database;
- a promise that data never leaves the device or that the product is 100% private/secure.

The milestone changes product presentation and interaction architecture only. Model artifacts, datasets, preprocessing, thresholds, evaluation metrics, and backend scientific behavior remain outside its scope.
