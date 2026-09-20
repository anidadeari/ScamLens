# ScamLens Design System

This document describes the design system implemented by the ScamLens frontend in Milestone 23. It is a product contract for the existing interface, not a generic style guide.

## Visual principles

ScamLens is calm, technical, and evidence-led. The interface uses a dark neutral foundation, restrained teal accent, compact typography, and clear borders. Decoration stays subordinate to analysis. Visual emphasis communicates hierarchy or evidence category; it never implies certainty.

The design intentionally avoids security-theater patterns: no threat maps, fake scanning effects, protection counters, neon warning fields, trust badges, or invented activity. Transitions are short and functional. There is no separate light theme.

## Tokens

Tokens live in `frontend/app/globals.css` under `:root`.

### Color and surfaces

| Role | Token | Current value | Use |
| --- | --- | --- | --- |
| Canvas | `--bg` | `#070b11` | Application background |
| Surface | `--surface` | `#0d131c` | Forms and result panels |
| Raised surface | `--surface-raised` | `#111a25` | Headers and emphasized cards |
| Soft surface | `--surface-soft` | `#0a1119` | Quiet callouts and supporting regions |
| Border | `--border` | `#223041` | Default separation |
| Strong border | `--border-strong` | `#33465b` | Emphasized boundaries |
| Primary text | `--text` | `#f3f7fb` | Titles and important labels |
| Secondary text | `--text-muted` | `#9aa9ba` | Explanations and body copy |
| Tertiary text | `--text-faint` | `#8292a6` | Metadata and subordinate technical text |
| Accent | `--accent` | `#60d9c3` | Primary actions and active context |
| Focus | `--focus` | `#a8efe2` | Keyboard focus ring |
| Success/ready | `--success` | `#70d6a1` | API readiness only, never safety |
| Warning | `--caution` | `#e8bc69` | Experimental scope and limitations |
| Error | `--danger` | `#ef858c` | Validation and service failures |

Result categories use `--model`, `--observation`, `--limitation`, and `--guidance`. These colors label the source or purpose of information. They are not risk levels.

Surfaces use `--radius-sm` (10 px), `--radius` (16 px), and `--radius-lg` (22 px). Shadows appear only on raised navigation, the analysis panel, or hovered actionable cards. Most grouping relies on borders and spacing.

### Typography

The frontend uses the system sans-serif stack and does not fetch a remote font. Monospace is reserved for classifier values, thresholds, workflow numbers, and submitted URL strings.

- Product identity: 18 px, strong weight.
- Overview title: responsive 38–56 px; 36–48 px on narrow mobile.
- Page title: responsive 38–64 px.
- Section title: responsive 29–47 px.
- Card/result title: 19–22 px.
- Body copy: 13–16 px with generous line height.
- Labels: 12 px, strong weight.
- Eyebrows and technical metadata: 10–11 px, uppercase, increased tracking.

Titles use compact letter spacing, while body text prioritizes readable line length. Explanatory copy is constrained by `--content-readable` (760 px). Helper, limitation, verification, observation, and metric-explanation text generally uses 12–13.5 px with at least 1.5 line height; tertiary styling is reserved for metadata, not material caveats.

### Spacing and width

The core spacing tokens are 4, 8, 12, 16, 24, and 32 px (`--space-1` through `--space-8`). Larger section spacing uses responsive `clamp()` values based on this rhythm. The fixed desktop sidebar is 272 px wide. Main content is capped with `--content-wide` (1320 px), plus shell padding.

Cards size to their own content by default. Multi-column result and context grids align cards at the top rather than stretching short limitations, empty observations, or verification panels to match a longer neighbor. Analysis workspaces and result regions use an intentional 1180 px maximum while retaining comfortable form widths. Density reductions target unused padding and repeated vertical space; they do not hide scientific context.

## Component patterns

### Navigation and shell

Desktop uses a persistent sidebar with Overview, Analyze, and Transparency groups. The current route uses `aria-current="page"`, an accent border, and an edge marker. At 820 px and below, the same semantic groups move into a native `details` menu with a 44 px trigger.

The top context bar contains low-key, deployment-neutral API availability: **System ready / API connected** or **API unavailable / Analysis service not connected**. Green means only that the API responded; it does not mean content is safe or that protection is active.

### Buttons and inputs

Primary buttons perform the explicit analysis action. Secondary buttons navigate to supporting information or select files. Quiet buttons handle low-emphasis actions such as removing an image. Interactive controls have a minimum height of 44 px, visible focus outlines, and distinct disabled styling.

Inputs always have a visible label, constraint text, and relevant helper/privacy text. Character and file constraints appear in the input workspace. Loading disables duplicate submission while request-generation guards prevent stale results from taking ownership of the UI.

### Feedback states

`StatePanel` presents empty, loading, caution, success, error, or unavailable states with text and a restrained status marker. Loading animations are opacity-only and are disabled by reduced-motion preferences. `ResultError` uses an alert role, plain language, and sanitized messages.

### Result composition

Results use small primitives rather than a single conditional component:

- `AnalysisResultShell` controls vertical rhythm.
- `ResultHeading` presents the model assessment and its critical interpretation.
- `ScoreBar` exposes exact returned values through a semantic meter.
- `ResultPanel` labels Model output, Observed indicators, Limitations, or Verification.
- `ScopeDetails` progressively discloses technical scope and additional limitations.
- `InfoCallout` presents disagreement and critical scope messages.
- `NumberedList` presents ordered verification guidance.

The critical safety limitation stays beside the assessment. Additional details may be expanded, but are never removed to simplify the appearance. Valid, Ham, and Benign use neutral presentation—not a success treatment.

Screenshot results add a compact **Analyzed as Email** or **Analyzed as Message** context label immediately before the reused result composition. This label records the user-selected analysis mode and is not a prediction.

Model Performance uses human-readable scope labels in primary presentation. Exact API scope identifiers remain visible in evaluation-context technical details, preserving the underlying scientific value without making raw identifiers the only explanation.

## Status semantics

- Accent: active navigation, primary action, or directly observed content.
- Neutral: ordinary scope and non-safety model states.
- Warning: experimental scope, disagreements, and limitations.
- Error: invalid input or unavailable/failed processing.
- Success/ready: operational API availability only.
- Model: experimental classifier output, always labeled as such.

No color is the sole carrier of meaning. Text labels remain visible for every state.

## Accessibility principles

The implementation favors native links, buttons, labels, lists, fieldsets, details, meters, and navigation landmarks. Async status regions use `aria-live`; loading result regions also expose `aria-busy`. Focus uses a high-contrast two-pixel ring with an offset. A skip link moves keyboard users to the main content.

File upload retains a keyboard-operable labeled input even though drag and drop is available. Screenshot stages are an ordered list and mark the current stage with `aria-current="step"`. Decorative icons are hidden from assistive technology. Reduced-motion settings remove meaningful animation duration and smooth scrolling.

The target is WCAG 2.2 AA-compatible interaction and contrast where reasonably possible. Automated semantics tests complement, but do not replace, manual keyboard and screen-reader review.

## Responsive principles

The checked viewports are 1440×900, 1280×800, 768×1024, and 390×844. Breakpoints are implemented at 1280, 1180, 1080, 820, 700, and 580 px.

- Large desktop and laptop retain the stable sidebar.
- At 820 px the sidebar becomes the native mobile menu and content uses the full viewport.
- Multi-column result and form layouts stack when their content would become cramped.
- The five-step screenshot rail becomes a two-column progression on narrow screens.
- Overview workflow cards reduce from five to three, two, and then one column.
- Performance metrics stack rather than becoming a compressed table.
- Long filenames and URL strings wrap inside their containers.

Primary actions remain visible and at least 44 px high. The page canvas suppresses unintended horizontal overflow, while individual content is designed to wrap instead of relying on clipping.

## Language and tone

Use “model output” or “model assessment,” not verdict, diagnosis, or threat determination. State limitations directly and calmly. Use “experimental” where scientifically required. Scores are classifier outputs unless calibration is established.

Never describe Ham as safe, Valid as authentic, Benign as trusted, or Phishing/Spam as proof of fraud. Do not claim external verification, URL reputation, real-time threat intelligence, perfect OCR, complete privacy, or guaranteed security. Privacy statements use the precise phrase “not intentionally persisted” and acknowledge that content reaches the configured ScamLens API.
