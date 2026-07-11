# Data-Leak Detection Checklist

Data leakage is any path by which information from the test set (or the future,
or the answer) reaches the model or the metric. It produces scores that look
excellent and do not generalize. Run every applicable check below before
reporting; treat a failure as a blocker, not a footnote.

## The six-check screen

```python
import numpy as np

# 1. Preserved input window (time-series / PDE rollouts): the given initial
#    condition must be echoed back BIT-for-BIT — the model must not "predict"
#    what it was handed.
assert np.allclose(preds[:, :, :init_step], targets[:, :, :init_step], atol=1e-10)

# 2. Predictions actually differ from targets in the PREDICTED window — catches
#    an accidental identity/copy of the target into the output.
assert not np.allclose(preds[:, :, init_step:], targets[:, :, init_step:], atol=1e-6)

# 3. No sample appears in both train and test (exact-duplicate hashing).
train_hashes = {hash(x.tobytes()) for x in train_data}
test_hashes  = {hash(x.tobytes()) for x in test_data}
assert len(train_hashes & test_hashes) == 0

# 4. Test set never enters a gradient path. Verify by inspection: every use of
#    test_loader is inside torch.no_grad() (or model.eval() + no optimizer step).
#    There is no assertion for this — it is a code-audit item.

# 5. No NaN / Inf in predictions (silently poisons or flatters aggregate metrics).
assert not np.isnan(preds).any() and not np.isinf(preds).any()

# 6. Error distribution is physically plausible: a large fraction of near-zero
#    per-sample errors is a leakage smell, not a triumph.
per_sample_error = compute_per_sample_error(preds, targets)
assert (per_sample_error < 1e-6).mean() < 0.01   # <1% near-perfect samples
```

`init_step` is the number of leading timesteps handed to the model as the
initial condition; adapt the axis indexing to your tensor layout. For
non-sequential tasks, checks 1 and 2 do not apply — the rest do.

## Leakage sources the six checks do not catch

The screen above catches the blatant cases. These subtler ones require a review
of the *pipeline*, not just the outputs:

- **Preprocessing fit on the full dataset.** Normalization statistics (mean/std,
  min/max), PCA bases, tokenizer vocabularies, target encoders, and imputation
  values must be fit on **train only**, then applied to val/test. Fitting a
  scaler on all data before splitting leaks the test distribution into training.
- **Feature engineering across the boundary.** Any feature computed with a window
  or aggregate that reaches across time (rolling means, "days since last event",
  group-level target means) can pull future or test information into a train
  row. Compute such features within each split, or with strict causality.
- **Group leakage.** Multiple rows from the same entity (patient, user,
  simulation seed, document) split across train and test let the model memorize
  the entity. Split by group (see `splits-and-protocol.md`).
- **Near-duplicates.** Augmented copies, resampled variants, and reposted content
  are not caught by exact hashing. De-duplicate with a similarity threshold
  (perceptual hash, embedding cosine, MinHash) before splitting when the domain
  has duplicates.
- **Target leakage in features.** A feature that is a proxy for, or downstream
  of, the label (e.g. a field only populated after the outcome is known) gives
  unrealistically high accuracy. Audit each feature: could it be known at
  prediction time?
- **Label leakage through metadata.** Filenames, IDs, sort order, or file
  timestamps that correlate with the label let a model cheat via a spurious
  channel. Strip or randomize order-carrying metadata.

## What to do on a failure

A failed check means the reported number is not trustworthy — do not "note it
and move on". Fix the pipeline (re-fit preprocessing on train only, re-split by
group, de-duplicate) and re-run the full evaluation from a clean split. If a
leak is discovered *after* reporting, the number must be retracted and
recomputed, not annotated.
