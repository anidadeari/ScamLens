# Email Model Card

## Model summary

This artifact is a controlled, exploratory three-class email baseline for
`Valid`, `Spam`, and `Phishing`. Its evaluation scope is **within corpus only**.
Real-world, source-independent, and user-independent generalization are not
established.

The sklearn Pipeline combines word TF-IDF with multinomial-compatible Logistic
Regression. It was trained on 3631
rows with random seed 42. Only the redacted Subject and Body text are
model input. No source, UID, ID, language, filename, split, duplicate-group,
contributor, or translation metadata is used as a feature.

## Data and evaluation

The source is version 1 of the Mendeley *Multilingual Phishing Email Dataset for
Low-Resource Languages*. The English anchor was prepared with deterministic
privacy redaction, and normalized duplicate groups were kept within one fixed
train/validation/test split. Translation variants were excluded.

The corpus is imbalanced: Valid is about 71%, Spam 20%, and Phishing 9%. Model
selection used validation macro-F1 over a small declared grid. Test was evaluated
once after the selection was frozen.

- Validation accuracy: 0.948254
- Validation macro-F1: 0.869201
- Test accuracy: 0.953608
- Test macro-F1: 0.885511
- Test weighted-F1: 0.953194

### Test performance by class

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| Valid | 0.989209 | 0.996377 | 0.992780 | 552 |
| Spam | 0.896774 | 0.885350 | 0.891026 | 157 |
| Phishing | 0.784615 | 0.761194 | 0.772727 | 67 |

Confusion-matrix values and complete validation/test metrics are stored in the
artifact directory.

## Intended use

- Reproducible technical exploration of a three-class text classifier.
- Comparing simple baselines within this exact prepared corpus.
- Testing future local application integration after explicit approval.

## Limitations and known failure modes

- The audit concluded Decision B: meaningful source-aware generalization is not
  supported by the corpus.
- Valid mail is concentrated in only three source values, and class is strongly
  associated with mbox/eml provenance.
- Removing metadata does not remove vocabulary, topic, formatting, campaign, or
  collection artifacts embedded in Subject and Body.
- Privacy redaction reduces exposure but cannot guarantee that every personal or
  contextual identifier was removed.
- Surface duplicate grouping cannot detect every semantic paraphrase.
- Class imbalance makes accuracy insufficient; macro-F1 and Phishing/Spam
  precision and recall must be considered.
- The label annotation procedure and collection period are not fully documented.

## Prohibited interpretation

This model must not be described as a production phishing detector, evidence of
real-world generalization, source-independent performance, user-independent
performance, or proof that an individual email is safe or malicious.
