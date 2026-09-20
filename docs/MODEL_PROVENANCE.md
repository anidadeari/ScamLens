# Trained model artifact provenance

These are read-only records for the approved artifacts. A structural inspection
found sklearn TF-IDF vocabularies and Logistic Regression parameters, with no
bundle key containing explicit rows/messages/emails/URLs. That does **not**
prove absence of memorization or eliminate source-content, privacy, or
derivative-rights risk.

| Artifact | Provenance and processing | Structural finding | Redistribution status |
| --- | --- | --- | --- |
| `artifacts/message/sms_spam_ham_pipeline.joblib` | SHA-256 `16b4738f5e09011a9408de3ad382365f1f14bd3c41a9ce63fe65f0cda33cc8c2`; produced by `scripts/train_message_model.py` from prepared UCI SMS data and `message_split_manifest.csv`; word TF-IDF 1–2 grams, lowercase, `min_df=2`, sublinear TF; Logistic Regression C=2; separate threshold 0.40; experimental SMS spam/ham purpose | Bundle keys: labels, pipeline, task, threshold; 10,821 vocabulary entries; no explicit source-row collection key | **CONDITIONAL / UNRESOLVED**: current UCI catalog says CC BY 4.0, but exact archive/constituent and trained-derivative treatment need review; attribution required |
| `artifacts/email/baseline_v1/email_pipeline.joblib` | SHA-256 `f76cf67f0259c71b12430f23122d5b1903a2cbbd62c6e9e5c4754060e41f4adb`; produced by `scripts/train_email_model.py` from Mendeley English subject/body data; word TF-IDF 1–2 grams, lowercase, `min_df=2`, sublinear TF; balanced Logistic Regression C=2; exploratory three-class purpose | Bundle keys contain pipeline/task/labels/scope metadata; 87,679 vocabulary entries; no explicit source-row collection key | **BLOCKED** for public redistribution pending email privacy/third-party-rights and derivative-model review |
| `artifacts/url/baseline_v1/url_pipeline.joblib` | SHA-256 `792f40cba0ad9aadf05ba762737a3e53abfaa23b3677582965c8f2fde3777552`; produced by `scripts/train_url_model.py` from the pinned PhreshPhish URL-only subset; character TF-IDF 4–6 grams, `min_df=5`, sublinear TF, 100,000 cap; balanced Logistic Regression C=2; anti-phishing research purpose | Bundle keys contain revision/scope/pipeline/task/labels; 100,000 vocabulary entries; no explicit source-row collection key | **UNRESOLVED**: attribution required; CC BY/anti-phishing wording and model redistribution need explicit or qualified resolution |

The joblib files also depend on compatible Python/scikit-learn/numpy/scipy/joblib
runtime components. Serialization does not confer a new license on dataset
material, and the ScamLens source license—once chosen—cannot relicense these
third-party-derived artifacts.
