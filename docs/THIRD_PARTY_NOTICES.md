# Third-party notices and dependency inventory

This factual inventory is not a project license or legal advice. It does not
relicense datasets, models, dependencies, or embedded content. Before shipping
a source archive or container, generate notices from the exact final dependency
closure and preserve the license/copyright files required by that closure.

## Dataset attributions

- **UCI SMS Spam Collection:** Tiago Almeida and José María Gómez Hidalgo,
  UCI dataset 228, DOI `10.24432/C5CC84`; the current official catalog states
  CC BY 4.0. The exact bundled v1 readme contains an older notice; see
  `DATASET_PROVENANCE.md` before redistribution.
- **Multilingual Phishing Email Dataset for Low-Resource Languages:** Youmna
  Abdelwahab, Kristian Eieland, Nadia Saad Noori; Mendeley Data v1,
  DOI `10.17632/btjg6kjj5h.1`; publisher displays CC BY 4.0. Embedded-content
  and privacy rights remain unresolved.
- **PhreshPhish:** Thomas Dalton, Hemanth Gowda, Girish Rao, Sachin Pargi,
  Alireza Hadj Khodabakhshi, Joseph Rombs, Stephan Jou, and Manish Marwah;
  v1.0.1; CC BY 4.0 label plus anti-phishing-research wording; cite
  arXiv:2507.10854. Terms ambiguity remains open.

## OCR components actually used

ScamLens invokes the environment-provided `tesseract` executable with
`lang="eng"`; it does not bundle the executable or traineddata today.

| Component | Installed evidence | Upstream/license evidence | Distribution implication |
| --- | --- | --- | --- |
| Tesseract OCR | 5.3.4, Ubuntu package `5.3.4-1build5` | [Official project](https://github.com/tesseract-ocr/tesseract): Apache-2.0; notes separately licensed dependencies | A future image must carry Apache-2.0 notices and inventory system libraries |
| Leptonica | 1.82.0 | Tesseract identifies Leptonica; installed package notice is BSD 2-clause | Preserve its copyright, conditions, and disclaimer if bundled |
| English traineddata | Ubuntu `tesseract-ocr-eng` 1:4.1.0-2, from `tessdata_fast`; local path `/usr/share/tesseract-ocr/5/tessdata/eng.traineddata` | [Official tessdata repositories](https://github.com/tesseract-ocr/tessdata) state Apache-2.0; installed package notice identifies `tessdata_fast` and Apache-2.0 | Preserve traineddata provenance and Apache-2.0 notice in a future image |

The installed binary also reports image/archive/compression and other linked
system libraries. The final image’s package-manager copyright inventory—not
this development-machine snapshot—must determine the complete notice set.

## Python direct dependencies

Versions are pinned in `requirements.txt`; license labels below come from the
installed distribution metadata. “Runtime” means used by FastAPI/legacy local
app or required to load artifacts, not that wheels are committed here.

| Package/version | Role | Metadata license label | Redistribution note |
| --- | --- | --- | --- |
| pandas 2.2.3 | training/evaluation and legacy app | BSD 3-Clause | Preserve notice if packaged |
| scikit-learn 1.6.1 | inference and training | BSD 3-Clause | Runtime-required for models; preserve notice |
| streamlit 1.45.1 | legacy local UI | Apache-2.0 | Not needed if only Next.js/FastAPI ships |
| numpy 2.2.6 | model runtime | BSD-style metadata text | Preserve distribution notices |
| scipy 1.15.3 | model runtime | BSD-style metadata text | Wheel includes components such as LGPL libquadmath; final wheel notices require review |
| joblib 1.5.1 | artifact loading | BSD 3-Clause | Runtime-required; preserve notice |
| pytest 8.3.5 | test only | MIT | Exclude from production runtime |
| pyarrow 25.0.1 | data preparation/evaluation | Apache-2.0 | Not required by current FastAPI inference paths |
| requests 2.34.2 | data-retrieval scripts/tests | Apache-2.0 | No submitted-URL runtime use; exclude if packaging only runtime |
| pytesseract 0.3.13 | OCR wrapper | Apache-2.0 | Runtime-required; preserve notice |
| fastapi 0.115.12 | backend runtime | MIT | Preserve notice |
| uvicorn 0.34.2 | backend server | BSD-3-Clause | Preserve notice |
| httpx 0.28.1 | tests only in this repository | BSD-3-Clause | Exclude from production runtime if not otherwise required |
| python-multipart 0.0.20 | upload parsing | Apache-2.0 | Runtime-required; preserve notice |
| anyio 4.9.0 | async runtime | MIT | Runtime/transitive; preserve notice |
| pydantic 2.13.5 | API validation | MIT | Runtime-required; preserve notice |

Important runtime transitives include Starlette, Pillow, annotated-types,
pydantic-core, typing-extensions, sniffio, click, and h11. Local metadata did
not flag non-commercial/proprietary licenses, but this is not a compatibility
opinion. A final environment may select different wheels and native libraries;
produce an exact Software Bill of Materials and retain every included license.

## Frontend dependency closure

Direct runtime packages are Next.js 16.3.5, React 19.3.0, and React DOM 19.3.0;
their installed package metadata and bundled license files say MIT. The
lockfile-derived production closure has 54 package names including optional
platform binaries. License labels comprise MIT, Apache-2.0, BSD-3-Clause, ISC,
0BSD, CC-BY-4.0, and the following material copyleft item:

- Sharp’s optional prebuilt `@img/sharp-libvips-*` packages identify
  `LGPL-3.0-or-later`; platform packages may combine Apache-2.0, LGPL-3.0-or-later,
  and MIT. A distributed production `node_modules` tree or image must include
  only the selected platform closure and satisfy the libvips LGPL notices and
  corresponding-library obligations. This must be verified on the final build.

Other production names include `@next/env`, platform `@next/swc-*`,
`@swc/helpers`, `styled-jsx`, `scheduler`, `postcss`, `nanoid`, `picocolors`,
`source-map-js`, `semver`, `caniuse-lite`, `baseline-browser-mapping`, `tslib`,
Sharp and its `@emnapi`/`@napi-rs` runtime packages. Dev dependencies
(TypeScript, ESLint, Vitest, jsdom, Testing Library, Tailwind/PostCSS tooling and
types) are build/test-only unless the final packaging method includes them.

Browser-delivered output contains compiled Next/React application code. No
external font, image CDN, third-party script, or analytics asset is referenced.
The logo and navigation icons are repository-authored TSX SVG paths; other
visuals are CSS-generated or local user-upload previews. Repository evidence
does not establish institutional/employment/course ownership of those original
assets or source.

## Project source

There is no root project `LICENSE`, copyright declaration, contributor
agreement, or evidence proving who has authority to license all original
ScamLens source. No copied third-party source was identified by repository text
search, but absence of a marker is not proof of authorship.

**PROJECT LICENSE DECISION REQUIRED FROM OWNER.** A future owner-approved
license would cover only source/assets within the owner’s authority. It cannot
relicense datasets, trained artifacts, dependencies, or third-party content;
those notices and gates remain separate.
