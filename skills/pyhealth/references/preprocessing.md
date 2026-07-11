# Preprocessing

Most PyHealth preprocessing is **automatic**. When you call `set_task` and then
construct a model with `feature_keys`/`label_key`, PyHealth builds the
vocabularies, tokenizes codes, pads variable-length sequences (via
`get_dataloader`'s collate), and shapes tensors for you. You rarely instantiate
low-level processors by hand, and their class names/signatures are internal and
version-specific — do not hard-code them without checking `pyhealth.__version__`
and the API docs. This reference covers the knobs that actually change results.

## Sequence Handling

Clinical event sequences vary wildly in length. The levers that matter:

- **Max length** — capping sequence length trades context for memory/speed.
  Rough guide: 20-50 (fast, less history), 50-100 (balanced), 100+ (more
  history, quadratic cost on `Transformer`). If you hit OOM, shorten this first.
- **Truncation side** — for clinical prediction, keep the **most recent** events
  (truncate the front). Recency usually carries the signal.
- **Padding** — handled for you in batching; you do not pad manually.

Where these knobs live differs by version (model constructor arg vs. a processor
vs. task config) — locate the one your version exposes rather than assuming.

## Feature Vocabularies

Code features become embeddings over a learned vocabulary. Two decisions:

- **Minimum frequency** — drop ultra-rare codes (e.g. seen < 5 times); they add
  parameters without signal and bloat the embedding table.
- **Grouping** — before building the vocabulary, consider collapsing codes to CCS
  categories or ATC drug classes (see `references/medical-coding.md`). This is
  the single most effective way to fight sparsity in small cohorts.

Rare codes outside the vocabulary map to an unknown/`<unk>` token.

## Numeric Features (labs, vitals)

- **Normalize** every continuous feature — z-score (mean 0, std 1) or min-max.
  Fit statistics on the **training split only**, then apply the same transform to
  val/test. Fitting on the full dataset leaks.
- **Impute** missing values explicitly (mean/median/forward-fill) and consider a
  missingness indicator — in EHR, *whether* a lab was ordered is itself signal.
- **Clip outliers** (e.g. at 3 SD) so a data-entry error doesn't dominate.

## Signals (EEG/ECG) and Images

Signal tasks expect windowed, filtered input (e.g. bandpass to the physiological
band, fixed sampling rate, fixed-length epochs such as 30-second sleep epochs).
Image tasks expect resized, normalized tensors, optionally augmented. PyHealth's
signal/image datasets and tasks apply the standard version of this for you; only
override when you have a specific reason and can validate the result.

## Class Imbalance

Rare-positive outcomes (mortality, readmission) need care at three points:

1. **Class weighting** in the loss where the model/loss supports it.
2. **Metric choice** — monitor `pr_auc`, report AUPRC alongside AUROC
   (`references/training-evaluation.md`).
3. **Threshold** — tune the decision threshold on validation, don't assume 0.5.

Never oversample across the patient-split boundary — duplicating a training
patient into the test set leaks.

## Validation of Preprocessing

Before training, spot-check: sample shapes are what the model expects, values
sit in the normalized range, no unexpected `NaN`, and the label prevalence
matches `dataset.stats()`. Cache expensive preprocessing (and set DataLoader
`num_workers`) so iteration stays fast.
