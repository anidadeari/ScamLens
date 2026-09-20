# Datasets

## PhreshPhish v1.0.1 URL-only experiment (Milestone 10)

Authoritative sources accessed 2026-09-15 were the [official dataset
card](https://huggingface.co/datasets/phreshphish/phreshphish), pinned revision
[`eabec4b7a66324b79cc8a0ad856d1731dc26fe1a`](https://huggingface.co/datasets/phreshphish/phreshphish/commit/eabec4b7a66324b79cc8a0ad856d1731dc26fe1a),
the [associated paper](https://arxiv.org/abs/2507.10854), and an [official
publisher clarification](https://huggingface.co/datasets/phreshphish/phreshphish/discussions/10).
The card identifies v1.0.1 (2026-02-07), CC BY 4.0, anti-phishing-research use,
paper citation for publications, and reasonable dataset attribution for
software/products. The dataset license—not merely the paper license—is stated
on the card. The publisher permits retained derived features and research that
may inform commercial anti-phishing products, subject to those terms.

The schema is `sha256`, `url`, `label`, `target`, `date`, `lang`, `lang_score`,
and `html`. Labels are `benign` and `phish`; they describe the released
collected webpages, not a guarantee about a submitted live site. The card calls
the data real-world rather than synthetic; synthetic examples are not
documented. The paper says phishing examples came from PhishTank, APWG eCrime
eXchange, and Netcraft, while benign examples came from anonymized Webroot
browsing telemetry; benign search results for targeted brands were used in
benchmark construction. The collection used rendered pages and therefore has
scraping-survivorship limitations. v1.0.1 adds data through December 2025, but
complete per-source counts and the exact updated v1.0.1 construction procedure
are not confirmed by the short card.

The publisher documents URL canonicalization/deduplication, content-similarity
filtering, quality filtering, manual review, and temporal organization. The
released train dates are 2024-07-02 through 2025-09-08 and test dates are
2025-09-08 through 2025-12-16; the boundary day overlaps. URL-only use is
schema-compatible, but it evaluates a narrower task than the paper's webpage
models and cannot inherit their conclusions.

### Retrieval and audit

`scripts/fetch_url_metadata.py` pins the revision and uses HTTP byte-range
Parquet projection for only `sha256`, `url`, `label`, and `date`, adding local
split/shard provenance. It aborts if a server ignores a range. It transferred
50,399,875 bytes and stored a 71,780,436-byte metadata Parquet instead of the
36.6 GB HTML corpus. No dataset URL was visited; `html` was never requested.

The 666,315 rows comprise 498,255 train and 168,060 test. Counts are 367,989
benign and 298,326 phish. Actual test counts are 91,260 benign and 76,800 phish;
the current card says 76,876 phish, which does not reconcile with its stated
test total and the pinned files. There are no missing URL/label/date values, no
exact duplicates, and no conflicting exact labels. Parsing finds 5,747 values
outside the supported URL contract (5,741 without HTTP(S), two with surrounding
whitespace, three with controls, one malformed); 18 additional URLs exceed the
2,048-character runtime limit. There are 235 normalized duplicate values (425
rows), none label-conflicting.

Audit normalization trims only for audit, lowercases and IDNA-encodes the
hostname, lowercases the scheme, removes HTTP 80/HTTPS 443, and drops fragments.
It retains userinfo, non-default ports, path, query, and other lexical content.
Raw text remains the classifier input; malformed values are never repaired.
Registered-domain grouping uses the local Public Suffix List with SHA-256
`02074b85e6f1454055b82aa7812bcea05f6afd9076e9a60ae1eb30ad61a26881`.

Across official train/test there are zero exact URL overlaps, two normalized
test-row overlaps, 56,456 test rows sharing a hostname, and 66,238 sharing a
registered domain with train (15,996 unique overlapping hostnames and 17,167
unique overlapping registered domains). Literal screening found 989 URLs
containing “phish” and 14 containing “benign”; these may be natural URL text,
so annotation leakage is not confirmed and nothing was silently removed.
Class availability varies sharply by month (including training months with no
benign rows), creating material collection-time/source confounding.

### Experiment design

The fixed-seed training subset contains 60,000 pre-2025-08-01 rows, allocated
proportionally by month and class and selected by SHA-256 rank: 31,317 benign
and 28,683 phish. Validation contains 27,823 later training-period rows on
registered domains absent from the earlier pool: 13,621 benign and 14,202
phish. The scored temporal test contains 166,494 supported rows after excluding
invalid/over-limit input and two normalized leaks: 89,707 benign and 76,787
phish. Test was not used for selection. The official split remains recorded in
the manifest; the filters are explicit rather than a replacement random split.

The prior DummyClassifier validation macro-F1 is 0.3287. Four small
character-TF-IDF/Logistic Regression candidates were compared. The selected
configuration uses character 4–6 grams, `min_df=5`, sublinear TF, at most
100,000 features, balanced class weights, and `C=2.0`. Character n-grams retain
local lexical/subword structure without network or page features.

Selected validation accuracy/macro-F1 are 0.8887/0.8885; phishing
precision/recall/F1 are 0.9459/0.8293/0.8838. Temporal-test
accuracy/macro-F1/weighted-F1 are 0.9249/0.9237/0.9244. Test phishing
precision/recall/F1 are 0.9641/0.8695/0.9143, with 2,486 false positives and
10,024 false negatives. The confusion matrix (`benign`, `phish`) is
`[[87221, 2486], [10024, 66763]]`.

Stored diagnostics show macro-F1 of 0.9150 (length 1–50), 0.9389 (51–100),
0.8692 (101–200), and only 0.4970 (201+). IP-literal and query-bearing subsets
also have macro-F1 near 0.50. Domain-seen/unseen-in-training-subset macro-F1 is
0.9177/0.9017. Error analysis stores only hashes and derived properties—not
URLs—and contains 2,486 false positives and 10,024 false negatives.

This is an experimental, prevalence-specific URL-string benchmark. Source/date
confounding, high domain overlap, label noise, scraping selection, temporal
drift, and weak long/query/IP diagnostics prevent safety or deployment claims.
No HTML, DNS, WHOIS, reputation, certificate, ownership, redirect, or live-site
information is available. HTTPS is not evidence of legitimacy.

## UCI SMS Spam Collection

ScamLens currently uses the UCI SMS Spam Collection only as a temporary,
experimental **spam/ham SMS classification baseline**. It is not a phishing,
scam, fraud, or email detection dataset, and results obtained from it must not
be presented as evidence of performance on any of those tasks.

### Source and attribution

- Official source: [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/228/sms+spam+collection)
- Dataset DOI: [10.24432/C5CC84](https://doi.org/10.24432/C5CC84)
- Creators: Tiago Almeida and José María Gómez Hidalgo
- Repository publication date: June 21, 2012
- Introductory paper: Almeida, T. A., Gómez Hidalgo, J. M., and Yamakami, A.
  (2011), *Contributions to the Study of SMS Spam Filtering: New Collection and
  Results*.

The dataset combines messages from the Grumbletext website, the NUS SMS
Corpus, Caroline Tagg's PhD thesis, and the SMS Spam Corpus v0.1 Big. The UCI
page describes the records as real SMS messages collected for mobile-phone
spam research.

### License and permitted use

The dataset is distributed under the [Creative Commons Attribution 4.0
International license](https://creativecommons.org/licenses/by/4.0/) (CC BY
4.0). Sharing and adaptation are permitted for any purpose when appropriate
credit is provided, a link to the license is included, and changes are
indicated.

Suggested attribution:

> Almeida, T. & Hidalgo, J. (2011). SMS Spam Collection [Dataset]. UCI Machine
> Learning Repository. https://doi.org/10.24432/C5CC84

### Local raw files

The official archive is preserved unchanged at
`data/raw/uci_sms_spam_collection.zip`. Its extracted source files are stored
under `data/raw/uci_sms_spam_collection/`:

- `SMSSpamCollection`: one tab-separated `label` and `message` record per line
- `readme`: the documentation distributed with the dataset

The preparation script does not overwrite either raw source file.

### Task definition

Each SMS is labeled `ham` (non-spam) or `spam`. The temporary model task is
binary SMS spam classification. The label must be preserved without mapping it
to phishing, fraud, scam, legitimacy, or safety.

### Preparation policy

Run:

```bash
.venv/bin/python scripts/prepare_message_data.py
```

The script validates the schema and expected labels, reports missing values and
exact duplicates, adds a one-based source `row_id`, and writes a reproducible
CSV and JSON statistics report under `data/processed/`. It preserves all rows,
labels, message text, and duplicates. No text normalization is applied.

### Limitations

- Spam/ham classification is not equivalent to phishing or fraud detection.
- The records are SMS messages rather than emails.
- The collection predates modern messaging patterns and LLM-generated text.
- It combines several sources with different populations and collection
  processes; many ham messages came from Singaporean users, while part of the
  spam collection came from a UK forum.
- The source records are not chronologically ordered, and per-message dates are
  unavailable, so temporal evaluation is not possible.
- Exact duplicates exist and must be considered before splitting data.
- A model trained on this collection must be described only as an experimental
  spam/ham SMS baseline and should not be used to make safety guarantees.

### Leakage-aware split

The split manifest is created with a fixed seed of 42. Exact messages are first
grouped by their SHA-256 digest. Potential near-duplicate texts are represented
with lowercase character-boundary TF-IDF features using 3–5 character n-grams.
Pairs with cosine similarity of at least 0.90 are joined into connected
components. Those components, rather than individual rows, are assigned to
approximately 70% train, 15% validation, and 15% test partitions.

This procedure prevents exact duplicates and the detected high-similarity
groups from crossing split boundaries. It does not eliminate every possible
form of leakage: lexical similarity cannot reliably detect paraphrases or
semantic equivalence, and 55 cross-split pairs were observed in the looser
0.80–0.90 audit range. The threshold was selected as a conservative,
documented preprocessing rule before model evaluation, not optimized against
test performance.

## Mendeley multilingual phishing-email candidate

This is an inspected candidate for a future, separate email model. It has not
been merged with the SMS data and has not been used to train or evaluate a
ScamLens model.

### Source, version, and license

- Dataset: [Multilingual Phishing Email Dataset for Low-Resource Languages](https://data.mendeley.com/datasets/btjg6kjj5h/1)
- DOI: [10.17632/btjg6kjj5h.1](https://doi.org/10.17632/btjg6kjj5h.1)
- Contributors: Youmna Abdelwahab, Kristian Eieland, and Nadia Saad Noori
- Repository publication: August 24, 2026, version 1
- Declared dataset license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

The Mendeley record applies CC BY 4.0 to the deposited dataset files, permitting
sharing and adaptation with attribution and an indication of changes. CC BY
4.0 does not guarantee that privacy, publicity, moral, or independently held
third-party rights are cleared. This matters here because the files contain
received emails and no anonymization statement was found in the record or the
archives. Raw messages must therefore remain private and excluded from Git and
public demonstrations pending a privacy and third-party-rights review.

The record says emails were collected from 11 users across regions and fields.
It does not document the collection period, annotators, label-assignment
criteria, adjudication, translation system, or a related peer-reviewed
publication. Those points remain unconfirmed. Archive timestamps and years
appearing in source filenames are not treated as message collection dates.

### Verified files

The official version-1 API exposed two downloadable ZIP archives. Copies are
stored under the ignored `data/raw/email/mendeley_multilingual_phishing_v1/`
directory and were inspected as data only; message URLs, HTML, and attachments
were not opened or executed.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `English_base.zip` | 3,166,767 | `286042af61564e2d8af54fb461348d86a097cbeb8486ecfc2d3218f0ae1c8b21` |
| `translation_output.zip` | 10,043,733 | `896d37a89072d4e6f3f069868ab470fc07b79d20f10504644d1e32ed5b6200bb` |

Both archives passed ZIP integrity checks. `English_base.zip` contains
`train.json`, `val.json`, and `test.json`. `translation_output.zip` contains
English subsets, Norwegian and Arabic derived variants, back-translated test
variants, and aggregate translation-audit JSON files. These variants reuse
stable `uid` values and are alternate representations of the same underlying
messages, not independent observations.

### Local inspection results

The English anchor has 5,180 rows: 3,729 train, 415 validation, and 1,036 test.
Its class counts are 3,687 `Valid`, 1,045 `Spam`, and 448 `Phishing`. Both
legitimate (`Valid`) and phishing emails are present, but spam is a distinct
third class and must not silently be mapped to either class.

All 5,180 `id` values and all 5,180 `uid` values are present and unique. Three
subjects are missing (two Spam and one Phishing), and one Spam body is missing.
There is one exact duplicate subject/body pair, with the same label, crossing
the published splits. After Unicode normalization, case folding, punctuation
removal, and whitespace collapse, 14 body-duplicate groups were found; five
cross the published splits and none has conflicting labels. This deterministic
audit only catches surface-form variants and does not detect semantic
paraphrases.

The `orig_lang` field reports 4,799 English, 246 Norwegian, 63 French, 15
Spanish, 12 Arabic, 10 Greek, 10 Catalan, 7 Danish, 7 Dutch, 3 Simplified
Chinese, 3 German, 2 Swedish, and one each of Portuguese, Turkish, and unknown.
The included audit says 380 of the 5,180 anchor rows were translated to English;
the exact translation method is not documented. Consequently, the English
anchor is mixed: primarily English-origin received emails plus translated,
derived text. The Norwegian and Arabic files are controlled translations and
must not be described as newly collected real emails in those languages.

The translated JSON files contain 829, 1,036, or 4,144 rows depending on the
experimental subset. Their class ratios mirror the linked anchor subsets. No
exact subject/body duplicates or label conflicts were found within an
individual translated file. The two 4,144-row mixed files inherit three
missing subjects and one missing body; the other derived files have no missing
field values. Combining these files without grouping on `uid` would create
direct cross-language and translation leakage.

### Suitability and leakage risks

The provenance fields expose 823 distinct source values. Only three source
values occur under more than one class. All 3,687 `Valid` rows came from mbox
containers, while the 817 individually named EML sources contain only Spam or
Phishing. This is a severe source/format confound: a random split can reward a
model for recognizing collection artifacts rather than phishing language.
Source filenames and message text may also contain personal information.

The dataset is suitable for controlled local exploration of a three-class
email task and potentially for a carefully redesigned binary
Phishing-versus-Valid experiment. It is not suitable as-is for a public demo or
as a trustworthy final benchmark. Before training, a future milestone should:

1. review and redact personal information without publishing raw messages;
2. obtain or reconstruct source-family and user-level groups, retaining `uid`;
3. reserve entire source families/users for external-style evaluation;
4. compare random/grouped results with leave-one-source-family-out results;
5. audit near-duplicates and translated variants across every split; and
6. document a defensible policy for the separate Spam class.

If user-level provenance cannot be recovered from the supplied metadata, that
limitation should block strong generalization claims. A separate legitimate
corpus should not be added automatically: pairing all phishing from one corpus
with all legitimate mail from another would intensify source-confounding and
would require source-balanced evaluation across multiple corpora.

### Controlled three-class preparation (Milestone 7)

The feasibility audit supports decision **B**: the data permit only a limited
within-corpus experiment. They do not currently support a defensible
source-group or user-group generalization experiment.

The record mentions 11 contributing users but supplies no user identifier or
documented mapping from rows to users. The `source` field is therefore not
treated as a user identity. It has 823 distinct values: only 3 support `Valid`,
539 support `Spam`, and 284 support `Phishing`. The three Valid-supporting
values contain 1,578, 1,417, and 692 rows and are class-exclusive. With a
15-percent holdout target of approximately 777 rows, only the 692-row group can
fit such a holdout. Giving each split one Valid source is technically possible,
but cannot produce two approximately 15-percent holdouts and would leave only
one Valid source per split. It would not establish user-level generalization.

For a future limited baseline, `scripts/prepare_email_data.py` creates a new
deterministic 70/15/15 within-corpus partition. It keeps all normalized
duplicate groups together and preserves `uid` only in the separate manifest.
The resulting split has:

| Split | Rows | Valid | Spam | Phishing | Duplicate groups |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 3,631 | 2,586 | 731 | 314 | 3,607 |
| Validation | 773 | 549 | 157 | 67 | 771 |
| Test | 776 | 552 | 157 | 67 | 774 |

Six hashed source values cross these new splits. This is intentional for the
limited within-corpus design and is also why its results must not be presented
as evidence of source-level generalization.

Only redacted Subject and Body text are designated as model input. Source,
filenames, `uid`, `id`, `orig_lang`, published split, and other metadata are
excluded from features. Missing fields are retained as empty strings. The same
deterministic redaction rules are applied to every class: visible text is
extracted from HTML-like bodies without loading resources, and supported email
addresses, URLs, IP addresses, phone-like strings, long numeric identifiers,
and names in common greeting forms are replaced with typed placeholders.
These rules reduce exposure but do not guarantee de-identification; personal
names in signatures and contextual identifiers may remain. Derived email files
remain excluded from Git pending a complete privacy review.

An aggregate label-leakage audit found no explicit `class:` or `label:`
annotation and no occurrences of known source-container names, Enron, or
Nazario. Natural message text does contain words such as “phishing”, “spam”,
“valid”, “legitimate”, and “dataset/corpus” across multiple classes; these were
reported but not silently removed because they may be genuine message content.
Metadata removal still cannot eliminate stylistic, topic, formatting, or
collection-source confounding.

Run the preparation once with:

```bash
.venv/bin/python scripts/prepare_email_data.py
```

Existing outputs require the explicit `--overwrite` option. The script writes
the redacted dataset, split manifest, configuration, and aggregate audit report
under `data/processed/`. It never reads `translation_output.zip` and performs no
model training.
