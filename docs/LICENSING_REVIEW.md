# Licensing and redistribution clearance matrix

This review records evidence and open gates; it is not legal advice. `CLEAR`
is not used where derivative rights, embedded content, ownership, or final
package notices remain unverified.

## Deployment distribution matrix

| Item | Source | License/terms | Evidence | In repository | Runtime requirement | Public repository redistribution | Production image redistribution | Attribution | Status | Action required |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ScamLens source | Repository-authored/unknown ownership scope | No project license | No root license or rights-holder declaration | Yes | Yes | Not authorized by repository evidence | Not authorized as source layer | Owner-dependent | **NEEDS OWNER DECISION** | Rights holder must confirm authority and select terms |
| SMS raw dataset | UCI SMS Spam Collection v1 | Current UCI: CC BY 4.0; bundled archive has older notice | Official UCI entry + bundled readme | Local, Git-ignored | No | Keep excluded pending notice/constituent review | Not needed | Yes | **NEEDS EXTERNAL VERIFICATION** | Reconcile exact archive notice/current catalog and constituent rights |
| SMS prepared dataset | ScamLens transformation of UCI data | Source terms continue to matter | Preparation scripts, hashes, manifests | Local, Git-ignored | No | Keep excluded | Not needed | Yes; mark changes | **NOT NEEDED IN PRODUCTION** | If distributed separately, complete source-rights review |
| SMS model | UCI-derived sklearn pipeline | Attribution expected; derivative treatment not explicit | Model provenance + official UCI entry | Yes | Yes | Do not publish yet | Private server use only pending review | Yes | **UNRESOLVED** | Qualified derivative/artifact review |
| Email raw dataset | Mendeley v1 | Publisher displays CC BY 4.0; embedded rights/privacy unconfirmed | Official DOI record + SOURCE.json | Local, Git-ignored | No | Do not distribute | Not needed | Yes | **BLOCKED** | Privacy/content/third-party-rights review |
| Email prepared dataset | ScamLens English subject/body CSV | Same unresolved source/content rights | Preparation report and manifest | Local, Git-ignored | No | Do not distribute | Not needed | Yes; mark changes | **BLOCKED** | Same qualified review |
| Email model | Mendeley-derived sklearn pipeline | Dataset license known; derivative/privacy status unresolved | Model provenance and structural inspection | Yes | Yes | Do not publish | Private server use requires rights/privacy assessment | Yes | **BLOCKED** | Qualified review before public model/service distribution |
| PhreshPhish raw HTML | PhreshPhish v1.0.1 | CC BY 4.0 label + anti-phishing-only wording | Official dataset card | No | No | Not applicable | Not needed | Yes | **NOT NEEDED IN PRODUCTION** | Do not acquire/package HTML for deployment |
| PhreshPhish URL metadata/raw strings | Pinned v1.0.1 revision | Same terms ambiguity | Provenance JSON/card | Local, Git-ignored | No | Keep excluded | Not needed | Yes | **UNRESOLVED** | Clarify terms and record-level distribution |
| URL prepared data | ScamLens URL-only subset/splits | Source terms continue to matter | Config/audit/manifests | Local, Git-ignored | No | Keep excluded | Not needed | Yes; mark changes | **NOT NEEDED IN PRODUCTION** | Qualified review if separately distributed |
| URL model | PhreshPhish-derived sklearn pipeline | CC BY + anti-phishing purpose; model distribution unaddressed | Model provenance; publisher clarification | Yes | Yes | Do not publish yet | Private anti-phishing use supported; redistribution unresolved | Yes | **UNRESOLVED** | Obtain explicit artifact clarification or qualified review |
| Stored metrics/evaluations | ScamLens aggregate outputs | Source provenance applies; no raw records intended | Artifact inspection | Yes | Performance endpoint only | Publish only with source/project clearance | Optional | Cite source experiments | **UNRESOLVED** | Include minimally or disable endpoint in packaging design |
| Tesseract | tesseract-ocr 5.3.4 | Apache-2.0 | Official project + installed package notice | No | Yes, environment-provided | Link/document only | Clear with required notices after final closure review | Yes | **CLEAR WITH ATTRIBUTION** | Preserve Apache notice and inventory linked libraries |
| English traineddata | tessdata_fast package 1:4.1.0-2 | Apache-2.0 | Official tessdata + installed package notice | No | Yes | Link/document only | Clear with required notice | Yes | **CLEAR WITH ATTRIBUTION** | Preserve exact traineddata source/version/license |
| Leptonica | System dependency 1.82.0 | BSD 2-clause | Tesseract docs + installed copyright | No | Tesseract dependency | Link/document only | Clear with notice | Yes | **CLEAR WITH ATTRIBUTION** | Preserve copyright/conditions/disclaimer |
| Python runtime dependencies | PyPI/install environment | Mainly permissive labels; native wheel notices vary | requirements + installed METADATA | Not vendored | Yes, selected subset | Requirements may be published only after project decision | Image redistributes selected wheels/native libs | Usually | **NEEDS EXTERNAL VERIFICATION** | Generate final-image SBOM/notices; review SciPy/native components |
| Frontend runtime dependencies | npm registry lock | Mostly permissive; Sharp/libvips includes LGPL-3.0-or-later | package-lock + installed licenses | Lockfile yes; node_modules ignored | Yes | Lockfile publication depends on project decision | Image may redistribute packages/native libvips | Yes | **NEEDS EXTERNAL VERIFICATION** | Final production closure and LGPL compliance review |
| Fonts/icons/assets | System fonts; TSX SVG/CSS visuals | Original ownership authority not established | Repository scan; no binary assets/fonts | Source only | Yes | Owner decision | Owner decision | Owner-dependent | **NEEDS OWNER DECISION** | Confirm source/icon authorship and ownership constraints |

## Distribution modes are not equivalent

| Action | Current conclusion |
| --- | --- |
| A. Make source code public | Requires owner authority and project-license decision; third-party notices remain separate |
| B. Distribute datasets | Transfers copies and triggers dataset terms plus privacy/content questions; raw/prepared email distribution is blocked |
| C. Distribute trained models | Transfers dataset-derived vocabulary/weights; not treated as automatically cleared by a dataset license |
| D. Use artifacts privately on a server | Does not distribute server files to users, but still requires lawful possession/use and privacy/data-processing assessment |
| E. Distribute a container/image | Redistributes every included model, wheel, npm/native package, Tesseract component, traineddata file, and notice; requires an exact final-image inventory |
| F. Offer a public web service without file downloads | Usually does not itself transfer server files, but does not resolve dataset purpose restrictions, privacy/data-protection, contractual terms, ownership, or provider logging |

## Current gate decisions

| Scenario | Decision | Evidence and remaining action |
| --- | --- | --- |
| Local private use | **PASS WITH ATTRIBUTION** | Existing sources describe research use; retain provenance/notices and do not redistribute |
| Private server deployment | **EXTERNAL VERIFICATION REQUIRED** | Email corpus privacy/third-party rights and operational data-processing obligations remain unresolved |
| Public web-service deployment | **BLOCKED** | Email rights/privacy, PhreshPhish terms ambiguity, project ownership, and provider/data-protection review remain open |
| Public source-code repository | **OWNER DECISION REQUIRED** | No project license or demonstrated authority; exclude raw/prepared data and gated models regardless |
| Public model redistribution | **BLOCKED** | Email model blocked; SMS/URL artifact derivative status unresolved |
| Raw/prepared dataset redistribution | **BLOCKED** | Email data blocked; UCI exact-notice/constituent and PhreshPhish terms questions remain |
| Container-image distribution | **BLOCKED** | Would combine gated models with software/native notice obligations; final closure absent |

## Qualified-review boundary

- Qualified legal/rights review recommended before redistributing any trained
  model, especially the email model.
- Qualified privacy/data-rights review recommended before any public service or
  distribution involving the email-derived model or corpus.
- Qualified review recommended before relying on the coexistence of
  PhreshPhish’s CC BY 4.0 label and anti-phishing-only wording.
- Owner/institutional review recommended before selecting a project license or
  publishing original source/assets.
- Final package compliance review recommended before distributing wheels,
  `node_modules`, Tesseract/traineddata, native libraries, or a container.

Until those actions are complete, licensing/redistribution remains a public
deployment gate. Nothing here grants permissions beyond the underlying terms.
