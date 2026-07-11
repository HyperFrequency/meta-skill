# Train / Val / Test Protocol

The single most common way a benchmark number gets inflated: the test set is
used for both model selection and the final metric. Selecting checkpoints,
hyperparameters, or early-stopping points on the same data you report on gives
an optimistic bias, typically 1-10% depending on how many decisions you made
against it.

## Wrong vs right

```python
# WRONG — one held-out set does double duty
train = data[:9000]     # 90%
test  = data[9000:]     # 10%  used for BOTH checkpoint selection AND the number
# every "which checkpoint is best?" peek leaks test information into the model

# RIGHT — three disjoint roles
n_train, n_val, n_test = 8000, 1000, 1000
train = data[:n_train]                                  # gradient updates
val   = data[n_train:n_train + n_val]                   # model selection
test  = data[n_train + n_val:n_train + n_val + n_test]  # final metric, ONCE
```

The three roles must never blur:

- **train** — the only data gradients ever see.
- **val** — every selection decision (checkpoint, learning rate, architecture,
  early stop). You may look at it as often as you like; that is its job.
- **test** — read exactly once, after all decisions are frozen, to produce the
  reported number. If you find yourself re-running on test after tweaking
  anything, you have contaminated it and need a fresh test set.

```python
best_val_metric = float("inf")
for epoch in range(num_epochs):
    train_one_epoch(model, train_loader)
    if epoch % eval_every == 0:
        val_metric = evaluate(model, val_loader)   # NOT test_loader
        if val_metric < best_val_metric:
            best_val_metric = val_metric
            save_checkpoint(model)

model = load_best_checkpoint()
reported_metric = evaluate(model, test_loader)      # once, at the very end
```

## When the benchmark defines no validation split

Some suites (several PDE benchmarks, older CV benchmarks, some Kaggle setups)
ship only train/test. You cannot invent a val split and still call it the same
benchmark, but you also should not select on test. Resolve it transparently:

1. Report the number under **their** protocol, exactly as they define it, so the
   comparison against prior work is apples-to-apples.
2. **Also** report a number under a proper train/val/test split (carved from the
   training data), which is the scientifically honest estimate of generalization.
3. State both in the paper and note that they differ and why. Do not silently
   pick whichever is lower.

If you must select *any* hyperparameter, select it on a validation split carved
out of training data — never on the benchmark's test set, even when the
benchmark itself blurs the line.

## Splits that are not random row slices

Random or contiguous slicing is only valid when samples are exchangeable. When
they are not, a naive split leaks:

- **Grouped data** (multiple samples per patient, per document, per simulation
  run): split by *group*, so no group appears in more than one set. Use
  `sklearn.model_selection.GroupKFold` / `GroupShuffleSplit`. Otherwise the
  model memorizes group identity and tests on the same group.
- **Temporal data** (time series, forecasting): split by *time* — train on the
  past, test on the future. Never shuffle across the time boundary; a future row
  in train leaks the answer for a past test row. For rolling evaluation, walk the
  window forward and keep an embargo gap if features look ahead.
- **Near-duplicates** (augmented copies, resampled variants, crawled data with
  reposts): de-duplicate *before* splitting, or duplicates straddle the boundary
  and act as leakage. See the duplicate-hashing check in
  `data-leak-checklist.md`.
- **Class imbalance**: stratify the split (`StratifiedKFold`) so rare classes
  appear in every set; otherwise variance across seeds explodes and the test
  metric is dominated by which rare samples happened to land where.

## Determinism

Make the split reproducible and pin it. A split that changes between runs makes
every downstream number unreproducible.

```python
rng = np.random.default_rng(seed=0)          # fixed seed for the split itself
perm = rng.permutation(len(data))
# persist perm (or the index lists) alongside results so the exact split is recoverable
```

Record the split sizes and the seed in your results artifact (see
`disclosure.md`), so a reviewer can reconstruct exactly which rows were where.
