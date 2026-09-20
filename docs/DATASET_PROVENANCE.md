# Dataset provenance and rights status

This is an evidence record, not legal advice. `VERIFIED` means the stated fact
was confirmed from the cited source; it does not mean every contemplated use is
legally cleared. Dataset licensing, embedded-content rights, privacy, and model
redistribution are assessed separately.

## UCI SMS Spam Collection v.1 — PARTIAL

| Field | Evidence |
| --- | --- |
| Identity | SMS Spam Collection, UCI dataset ID 228, DOI `10.24432/C5CC84`, 5,574 English SMS messages |
| Creators | Tiago Almeida and José María Gómez Hidalgo |
| Repository copy | `data/raw/uci_sms_spam_collection.zip` and extracted `SMSSpamCollection`/`readme`; archive SHA-256 `1587ea43e58e82b14ff1f5425c88e17f8496bfcdb67a583dbff9eefaf9963ce3` |
| Current official license display | [UCI’s official entry](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) states CC BY 4.0 and supplies the citation “Almeida, T. & Hidalgo, J. (2011). SMS Spam Collection [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CC84.” |
| Exact archive notice | The bundled upstream `readme` calls the corpus “v.1,” asks for citation and notification, reserves copyright to Almeida/Hidalgo, says it is free with “no limitations excepting” warranty/liability terms, and places responsibility for distribution, modification, reproduction, publication, and derivatives on the user. It does not itself mention CC BY 4.0. |
| Prepared provenance | `uci_sms_spam_baseline.csv`, its statistics, and the split manifest preserve row IDs/hashes and point to the exact source; preparation does not normalize message text. |
| Privacy/content evidence | The upstream readme says NUS contributors knew their messages would be made public, but the collection combines several sources and does not establish equivalent consent or third-party-content clearance for every message. |

CC BY 4.0 fact: the current official catalog permits sharing and adaptation
with attribution, a license reference, and change indication. Unresolved fact:
the repository does not establish when or how that catalog license applies to
the exact older archive notice or every constituent corpus. Raw/prepared public
redistribution and derivative-model clearance therefore remain subject to
qualified verification. Private local research use is supported by the
archive’s stated research purpose and existing provenance.

Recommended factual attribution:

> Almeida, T. & Hidalgo, J. (2011). SMS Spam Collection [Dataset]. UCI Machine
> Learning Repository. https://doi.org/10.24432/C5CC84. Current UCI catalog
> license: CC BY 4.0. ScamLens prepared splits and trained an experimental
> spam/ham baseline from the collection.

## Mendeley multilingual phishing email dataset v1 — PARTIAL

| Field | Evidence |
| --- | --- |
| Identity | *Multilingual Phishing Email Dataset for Low-Resource Languages*, version 1, published 24 August 2026, DOI `10.17632/btjg6kjj5h.1` |
| Contributors | Youmna Abdelwahab, Kristian Eieland, and Nadia Saad Noori; University of Agder is listed by the publisher |
| Authoritative source | [Mendeley Data record](https://data.mendeley.com/datasets/btjg6kjj5h/1) |
| Publisher license display | CC BY 4.0 is displayed for version 1 and the page offers the dataset files for download |
| Exact repository copy | `English_base.zip` SHA-256 `286042af…1c8b21`; `translation_output.zip` SHA-256 `896d37a8…6200bb`; exact source metadata is in `SOURCE.json` |
| Content | The publisher says messages came from 11 users across regions/fields and English data was extended through controlled Norwegian/Arabic translation |
| Repository inclusion | Raw archives and a prepared English three-class CSV containing subject/body content are present locally and Git-ignored |
| Missing evidence | No bundled license text, anonymization/redaction claim, participant consent terms, message-level provenance, third-party correspondence clearance, or explanation of how CC BY applies to embedded email content was found |

License status: the publisher’s dataset record states CC BY 4.0. Privacy and
third-party-rights status: **UNRESOLVED**. Derivative email-model redistribution:
**UNRESOLVED**. The dataset-level license is not treated as proof that private
correspondence, personal data, sender text, trademarks, or other embedded
rights are cleared. Raw and prepared email data must remain excluded from a
public repository, production package, and public downloadable distribution.

Qualified legal/rights review recommended before publishing the raw/prepared
email corpus, redistributing the email model, or providing a public service
whose model was trained on this corpus.

## PhreshPhish v1.0.1 — PARTIAL / TERMS AMBIGUITY

| Field | Evidence |
| --- | --- |
| Identity | `phreshphish/phreshphish`, v1.0.1 dated 7 February 2026, pinned revision `eabec4b7a66324b79cc8a0ad856d1731dc26fe1a` |
| Authoritative source | [Official dataset card](https://huggingface.co/datasets/phreshphish/phreshphish) and its [publisher clarification](https://huggingface.co/datasets/phreshphish/phreshphish/discussions/10) |
| License label | CC BY 4.0 |
| Additional wording | The same “License & Terms of Use” section says it “should only be used for anti-phishing research.” The repository evidence does not establish whether this is a binding additional restriction, a purpose statement/request, or how it coexists legally with standard CC BY 4.0 permissions. |
| Publisher clarification | An official organization maintainer said private research may inform commercial anti-phishing products, derived features may be retained, publications should cite the paper, software/products should reasonably attribute the dataset, and CC BY plus anti-phishing research are the requirements. This supports ScamLens’s anti-phishing purpose but does not expressly clear public model redistribution. |
| Citation | Dalton et al. (2025), *PhreshPhish: A Real-World, High-Quality, Large-Scale Phishing Website Dataset and Benchmark*, arXiv:2507.10854 |
| Repository content | No raw HTML is present. The local Parquet contains URL metadata/strings; prepared URL-only data, split manifests, audit files, metrics, and a trained URL model are present. Raw submitted/dataset URLs are not placed in error-analysis output. |

The URL classifier serves the same anti-phishing research/decision-support
purpose, but redistribution remains **UNRESOLVED** because the relationship
between CC BY 4.0 and the anti-phishing-only wording, and its application to a
trained artifact, requires qualified review or explicit upstream confirmation.

Qualified legal/rights review recommended before distributing PhreshPhish
records, prepared URL data, the URL model, or a container containing them.

## Data packaging policy

| Material | Runtime role | Packaging policy |
| --- | --- | --- |
| All raw datasets/archives | None | **DO NOT INCLUDE IN PRODUCTION PACKAGE** |
| Prepared training CSV/Parquet and split manifests | Training/reproducibility only | **DEVELOPMENT/TRAINING ONLY; DO NOT INCLUDE** |
| Audit/error-analysis files | Evaluation only | **EVALUATION ONLY; DO NOT INCLUDE** |
| Stored message/email/URL metrics | Read by `/api/performance` | Runtime-required only if that endpoint remains enabled; contain aggregate results, not source rows |
| Three joblib model bundles | Required for inference | **RUNTIME REQUIRED; redistribution status separately gated** |
| Model configuration/label metadata | Validation/documentation support | Include only the minimum files confirmed by the packaging manifest |

No dataset deletion is authorized or performed by this policy.
