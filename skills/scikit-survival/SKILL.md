---
name: scikit-survival
version: 0.1.0
description: >-
  Survival analysis and time-to-event modeling in Python with scikit-survival
  (import sksurv), a scikit-learn-compatible library for right-censored data.
  Use when building a Surv structured outcome from event/time; fitting Cox
  proportional hazards (CoxPHSurvivalAnalysis, penalized CoxnetSurvivalAnalysis,
  IPCRidge), Random Survival Forests, Gradient Boosting, or Survival SVM models;
  evaluating with concordance index (Harrell's or Uno's IPCW), time-dependent
  AUC, or (integrated) Brier score; estimating Kaplan-Meier / Nelson-Aalen
  curves; or analyzing competing risks via cumulative incidence and
  cause-specific hazards. Not for uncensored regression/classification (use
  scikit-learn), time-varying covariates, Fine-Gray sub-distribution models or
  formal proportional-hazards tests (use lifelines), or deep-learning survival
  models (use pycox/DeepSurv).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: GPL-3.0
---

# scikit-survival

## Overview

scikit-survival (imported as `sksurv`) implements survival analysis on top of
scikit-learn. Survival analysis models the **time until an event** while
correctly handling **censoring** — subjects whose event has not been observed by
the end of follow-up. The library primarily targets **right-censored** data and
reuses the sklearn contract: `fit`/`predict`, `Pipeline`, `GridSearchCV`, and
`cross_val_score` all work with survival estimators and survival-aware scorers.

The outcome `y` is not a scalar — it is a structured array pairing a boolean
event indicator with an observed time. Ordinary regression or classification
metrics are invalid here, so this skill also covers censoring-aware evaluation.
scikit-survival is licensed GPL-3.0; keep that in mind before vendoring it.

## When to Use This Skill

- Fitting Cox proportional hazards models — standard (`CoxPHSurvivalAnalysis`),
  elastic-net penalized for high-dimensional / `p > n` data
  (`CoxnetSurvivalAnalysis`), or the AFT-style `IPCRidge`.
- Building non-linear survival predictors: `RandomSurvivalForest`,
  `GradientBoostingSurvivalAnalysis`, `ComponentwiseGradientBoostingSurvivalAnalysis`,
  `ExtraSurvivalTrees`, or the survival SVMs.
- Constructing survival outcomes from raw `event`/`time` columns and preparing
  censored data (encoding, scaling, validation).
- Evaluating discrimination and calibration with concordance index,
  time-dependent AUC, or Brier score under censoring.
- Estimating non-parametric survival (Kaplan-Meier) or cumulative hazard
  (Nelson-Aalen) curves.
- Analyzing competing risks (multiple mutually exclusive event types) via
  cumulative incidence functions and cause-specific Cox models.

## When NOT to Use This Skill

- **No censoring** — every outcome is fully observed. Use plain regression or
  classification with `scikit-learn`; a survival model adds nothing.
- **Time-varying covariates** — sksurv fixes covariates at baseline. Use
  `lifelines` (time-varying Cox) or a landmarking / counting-process approach.
- **Fine-Gray sub-distribution hazard models** or **formal proportional-hazards
  tests** (Schoenfeld residuals) — not implemented in sksurv. Use `lifelines`
  or R's `cmprsk`/`survival`. sksurv covers cause-specific hazards only.
- **Deep-learning survival** (DeepSurv, DeepHit, neural CIF) — use `pycox` /
  `torchsurv`.
- **Interval- or left-censored data** — sksurv is built for right censoring.

## Setup

```bash
pip install scikit-survival        # or: conda install -c conda-forge scikit-survival
```

Depends on numpy, pandas, and scikit-learn. Import as `sksurv`.

## The Survival Outcome (`Surv`)

Every estimator expects `y` as a structured array with a boolean `event` field
and a numeric `time` field. Build it with `sksurv.util.Surv`:

```python
from sksurv.util import Surv

y = Surv.from_arrays(event=event_bool_array, time=time_array)   # from arrays
y = Surv.from_dataframe("event", "time", df)                    # from a DataFrame
```

`event=True` means the event was observed; `event=False` means the record was
censored at `time`. Times must be positive and finite. See
`references/data-handling.md` for loading (built-in datasets, CSV, ARFF),
categorical encoding, scaling, missing-value handling, quality checks, and
censoring-aware splits.

## Choosing a Model

```
Start
├─ High-dimensional (p > n) or need feature selection?
│    → CoxnetSurvivalAnalysis (elastic net; l1_ratio≈0.9 for Lasso-like)
├─ Need interpretable coefficients / hazard ratios?
│    → CoxPHSurvivalAnalysis  (or ComponentwiseGradientBoosting for sparse linear)
├─ Complex non-linear effects expected?
│    ├─ Large n (>1000)      → GradientBoostingSurvivalAnalysis
│    ├─ Medium n             → RandomSurvivalForest or FastKernelSurvivalSVM
│    └─ Small n              → RandomSurvivalForest / ExtraSurvivalTrees
└─ Otherwise (roughly linear) → CoxPHSurvivalAnalysis or FastSurvivalSVM
When unsure: fit several and compare with the same censoring-aware metric.
```

For per-family parameters, tuning grids, and interpretation, see
`references/cox-models.md`, `references/ensemble-models.md`, and
`references/svm-models.md` (also listed under Reference Files below).

All models expose `.predict()` (a risk score — higher means higher risk /
shorter survival). Tree ensembles and Cox models also expose
`.predict_survival_function()` and `.predict_cumulative_hazard_function()`.

## Evaluating Survival Models

Never use accuracy/R². Use censoring-aware metrics from `sksurv.metrics`:

- **Concordance index** (ranking): `concordance_index_censored` (Harrell's) for
  low censoring; `concordance_index_ipcw` (Uno's) when censoring exceeds ~40% —
  it needs `y_train` for the IPCW weights and is the more defensible default.
- **Time-dependent AUC**: `cumulative_dynamic_auc(y_train, y_test, risk, times)`
  for discrimination at specific horizons.
- **Brier score**: `brier_score` (one time) and `integrated_brier_score` (over a
  window) assess calibration + discrimination; they consume survival functions.
- **CV scorers**: wrap metrics with `as_concordance_index_ipcw_scorer()` /
  `as_integrated_brier_score_scorer()` to use them in `GridSearchCV`.

Report at least Uno's C-index plus one calibration metric. Full guidance,
interpretation ranges, and a reusable evaluation routine are in
`references/evaluation-metrics.md`.

## Non-parametric Estimation

Model-free curves from `sksurv.nonparametric`, taking `event` and `time`:

```python
from sksurv.nonparametric import kaplan_meier_estimator, nelson_aalen_estimator

time, survival_prob   = kaplan_meier_estimator(y["event"], y["time"])   # S(t)
time, cumulative_haz  = nelson_aalen_estimator(y["event"], y["time"])   # H(t)
```

Use these for exploratory group comparisons and as a baseline to beat.

## Competing Risks

When events are mutually exclusive (e.g. death from different causes), a
Kaplan-Meier estimate of one cause **overstates** its probability. Use the
cumulative incidence function instead. The estimator takes an **integer status
array** (0 = censored, 1..k = event type) and time, and returns `(times,
cif_estimates)` where `cif_estimates[0]` is total risk and `cif_estimates[i]` is
event type `i`:

```python
from sksurv.nonparametric import cumulative_incidence_competing_risks

times, cif = cumulative_incidence_competing_risks(status_int, time)
# cif[0] = total; cif[1], cif[2], ... = per-event-type CIF
```

For covariate effects, fit **cause-specific** Cox models (one per event type,
treating the others as censored). Fine-Gray sub-distribution models are not in
sksurv. See `references/competing-risks.md` for data layout, stratified plots,
cause-specific modeling, and common mistakes.

## scikit-learn Integration

Survival estimators drop into pipelines and search. The `as_*_scorer` helpers
**wrap the estimator** (they are not `scoring=` objects) so its `.score` returns
the survival metric; grid keys then take an `estimator__` prefix:

```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sksurv.metrics import as_concordance_index_ipcw_scorer

pipe = Pipeline([("scale", StandardScaler()), ("model", CoxPHSurvivalAnalysis())])
gcv = GridSearchCV(as_concordance_index_ipcw_scorer(pipe),
                   {"estimator__model__alpha": [0.1, 1.0, 10.0]}, cv=5)
gcv.fit(X, y)
```

## Common Pitfalls

- Harrell's C-index with heavy censoring — switch to Uno's (`concordance_index_ipcw`).
- Forgetting `y_train` in `concordance_index_ipcw` — required for IPCW weights.
- Not standardizing features for SVMs and penalized Cox — always scale first.
- Trusting a tree model's impurity feature importance — use
  `sklearn.inspection.permutation_importance` with a survival scorer.
- Treating a competing event as ordinary censoring for probability estimates —
  use cumulative incidence, not Kaplan-Meier.
- Too few events per feature — aim for roughly 10+ events per covariate, or
  regularize (Coxnet) / select features.
- Passing `as_*_scorer(...)` to `scoring=` — they wrap the estimator instead
  (prefix grid keys with `estimator__`), they are not `scoring=` objects.
- Ignoring the proportional-hazards assumption for Cox — check it (Schoenfeld
  residuals via lifelines) or use a non-PH model.

## Reference Files

- `references/data-handling.md` — data loading, encoding, scaling, missing
  values, validation, censoring-aware splits.
- `references/cox-models.md` — Cox PH, Coxnet, IPCRidge, regularization,
  interpretation, PH-assumption checks.
- `references/ensemble-models.md` — RSF, gradient boosting, componentwise
  boosting, extra trees, tuning, permutation importance.
- `references/svm-models.md` — survival SVM variants, kernels, clinical kernel,
  scaling, complexity.
- `references/evaluation-metrics.md` — C-index, time-dependent AUC, Brier score,
  CV scorers, full evaluation pipeline.
- `references/competing-risks.md` — cumulative incidence, cause-specific Cox
  models, stratified analysis, pitfalls.

## Key Imports

```python
from sksurv.util import Surv                                    # outcome construction
from sksurv.linear_model import CoxPHSurvivalAnalysis, CoxnetSurvivalAnalysis, IPCRidge
from sksurv.ensemble import RandomSurvivalForest, GradientBoostingSurvivalAnalysis
from sksurv.svm import FastSurvivalSVM, FastKernelSurvivalSVM
from sksurv.metrics import concordance_index_ipcw, integrated_brier_score, \
    cumulative_dynamic_auc, as_concordance_index_ipcw_scorer
from sksurv.nonparametric import kaplan_meier_estimator, cumulative_incidence_competing_risks
```

(Also available: `ComponentwiseGradientBoostingSurvivalAnalysis`,
`ExtraSurvivalTrees`, `sksurv.tree.SurvivalTree`,
`sksurv.preprocessing.encode_categorical`.)

## Additional Resources

- Docs: https://scikit-survival.readthedocs.io/ · Source: https://github.com/sebp/scikit-survival
- Related skills: `scikit-learn` (base estimators, pipelines, CV), `shap`
  (explaining tree survival models), `statistical-analysis`.
