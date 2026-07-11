---
name: ml-benchmark-evaluation
version: 0.1.0
description: >-
  Rigorous methodology for evaluating ML models against established benchmarks
  and published baselines. Enforces a clean train/val/test protocol,
  verification of baseline numbers from primary sources, exact-formula metric
  matching, a data-leakage detection checklist, multi-seed robustness, optional
  physics-informed consistency checks for scientific ML, and honest reporting
  templates. Use when claiming to beat a published baseline, writing a
  methods/results section that compares against prior work, or auditing an
  existing result for overfitting, leakage, or metric mismatch. NOT for general
  model interpretability (use `shap`), reproducing a paper's full pipeline
  end-to-end (use `repro-eval`), designing statistical tests or sample sizes
  (use `statistical-analysis`, `power-analysis`), verifying trading-strategy
  backtests (purged CV / deflated Sharpe belong to a strategy-verify workflow),
  or first-time model training with no benchmark comparison to make.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# ML Benchmark Evaluation

## Overview

A published benchmark number is a claim, and a claim that beats prior work
draws scrutiny. This skill gives you the discipline to make such a claim
survive it: split the data so model selection never touches the test set,
confirm the baseline you are comparing against from its primary source, compute
your metric with the *exact* formula the benchmark uses, screen for the handful
of leakage patterns that silently inflate scores, and report the result with
its seeds, splits, and confounders visible.

**The governing principle:** your evaluation protocol must be at least as strict
as the baseline you claim to beat — ideally stricter. If your protocol is looser
in any dimension (more test peeks, a friendlier metric variant, a bigger model
compared against a smaller one), the comparison is not yet fair and the number
is not yet publishable.

## When to Use This Skill

- Claiming to beat a published baseline on any ML benchmark.
- Writing a methods or results section that compares against prior work.
- Auditing an existing result for overfitting, data leakage, or a metric
  mismatch — your own or someone else's.
- Any evaluation where the reported number gates a decision (publication, model
  promotion, a go/no-go).
- Scientific-ML settings (PDE surrogates, simulation emulators) where physical
  consistency matters beyond the headline error metric.

## When NOT to Use This Skill

- Explaining *why* a model predicts what it does — use `shap` for feature
  attribution and interpretability.
- Reproducing a paper's entire training + eval pipeline end-to-end — use
  `repro-eval`; return here for the evaluation-rigor layer.
- Designing hypothesis tests, choosing a test statistic, or computing required
  sample sizes — use `statistical-analysis` and `power-analysis`.
- Validating a trading strategy's backtest (purged/embargoed CV, PBO, deflated
  Sharpe) — that is a strategy-verify concern, not a static-benchmark one.
- Training a model for the first time with no benchmark to compare against —
  there is no claim to defend yet.
- Judging the quality of a paper's argument or novelty — use `peer-review` or
  `scholar-evaluation`.

## The Evaluation Checklist

Run every applicable item before you report a number. Each links to depth.

1. **Splits are clean.** Three disjoint sets: train (gradients), val (model
   selection / checkpoints / early stopping), test (final metric, touched
   once). Never select on test. See
   [references/splits-and-protocol.md](references/splits-and-protocol.md).
2. **Baseline is verified from the primary source.** Never trust a number
   copied into a task description, blog, or secondary table. Parse the original
   paper and confirm the exact value, metric, and split. See
   [references/verify-baselines.md](references/verify-baselines.md).
3. **Metric formula matches exactly.** The same metric *name* (nRMSE, F1, mAP)
   often has several inequivalent definitions differing by 1-10%. Read the
   benchmark's own metrics code and reproduce it. See
   [references/metrics-and-formulas.md](references/metrics-and-formulas.md).
4. **No data leakage.** Work the leakage checklist: preserved input windows,
   train/test duplicate hashing, normalization stats fit on train only, no
   test tensor in a gradient path, sane error distribution. See
   [references/data-leak-checklist.md](references/data-leak-checklist.md).
5. **Result is robust across seeds.** Single-seed results can be lucky. Report
   mean ± std over ≥3 seeds for any headline claim.
6. **Confounders are documented.** If your model differs from the baseline in
   capacity, resolution, data, or budget, list every difference and isolate the
   real contribution with an ablation.
7. **Reporting is honest.** Show splits, seeds, both metric variants if in
   doubt, and the worst-case sample — never only the best epoch. See
   [references/disclosure.md](references/disclosure.md).

## Core Techniques (quick reference)

### Clean split, selection on val only

```python
n_train, n_val, n_test = 8000, 1000, 1000
train = data[:n_train]                              # gradient updates
val   = data[n_train:n_train + n_val]               # checkpoint selection
test  = data[n_train + n_val:n_train + n_val + n_test]  # reported metric, ONCE

# during training: select on val, never test
if epoch % eval_every == 0:
    val_metric = evaluate(model, val_loader)        # NOT test_loader
    if val_metric < best_val_metric:
        save_checkpoint(model)

# after training, exactly once:
model = load_best_checkpoint()
reported_metric = evaluate(model, test_loader)
```

When the benchmark defines no val split (common in some CV and PDE suites),
report *their* protocol for fair comparison **and** a proper-val-split number
for rigor, and be explicit that they differ. Details, plus grouped and temporal
splits, in [references/splits-and-protocol.md](references/splits-and-protocol.md).

### Multi-seed robustness

```python
seeds = [42, 123, 7, 2024, 31415]
scores = []
for seed in seeds:
    set_all_seeds(seed)                 # torch, numpy, python, cudnn-deterministic
    scores.append(evaluate(train(seed)))
print(f"{np.mean(scores):.4e} ± {np.std(scores):.4e}  (n={len(seeds)} seeds)")
```

Minimum for a publication-grade claim: 3 seeds, reported as mean ± std. A gap
between two methods smaller than the sum of their stds is not a real gap.

### Fastest way to spot a leak

If a large fraction of test samples have near-zero error, suspect leakage
before you celebrate:

```python
assert (per_sample_error < 1e-6).mean() < 0.01   # <1% near-perfect samples
```

The full six-check screen (including preserved-window checks for time-series /
PDE rollouts and train/test duplicate detection) is in
[references/data-leak-checklist.md](references/data-leak-checklist.md).

## Scientific-ML: validate the physics, not just the error

For PDE surrogates, simulation emulators, and other physically-grounded models,
a low error metric is necessary but not sufficient — the prediction must also
obey the physics. Check conservation drift, physical bounds (density ≥ 0),
symmetry, known analytical limits, rollout error growth, and spectral content.
The full criteria table lives in
[references/metrics-and-formulas.md](references/metrics-and-formulas.md#physics-informed-validation).

## Failure Modes and Pitfalls

The classic ways a benchmark number becomes wrong or misleading — selecting on
test, single-seed luck, trusting a secondary baseline, comparing across
non-equivalent metric variants, hiding confounders, cherry-picking the best
epoch, suppressing failure cases — are catalogued with their symptoms and fixes
in [references/disclosure.md](references/disclosure.md#common-pitfalls).

## Related Skills

- `repro-eval` — reproduce a paper's full pipeline; this skill supplies its
  evaluation-rigor layer.
- `statistical-analysis`, `power-analysis` — significance testing and sample
  sizing for the numbers this skill produces.
- `shap` — interpret an already-evaluated model's predictions.
- `peer-review`, `scholar-evaluation` — judge a paper's argument and novelty
  once its numbers are trustworthy.
- `claim-verify` — check an external factual claim (including a cited baseline)
  against primary sources.
