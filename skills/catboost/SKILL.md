---
name: catboost
version: 0.1.0
description: CatBoost gradient-boosted decision trees for tabular price-direction classification and time-series return prediction. Use when the user asks to "train a CatBoost model", "predict direction with CatBoost", "use CatBoostClassifier / CatBoostRegressor", has heavy categorical features (symbol, exchange, regime), or needs time-ordered training via `has_time=True` and the `TimeSeries` CV fold type. Covers the scikit-learn-style API, native string categoricals + CTR/target encoding, multi-target return forecasting with `loss_function="MultiRMSE"`, GPU training (`task_type="GPU"`), and Optuna tuning. Not for mostly-numeric features without categorical handling — use XGBoost (broader ecosystem) or LightGBM (CPU speed priority) instead.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: Apache-2.0
metadata:
    skill-author: HyperFrequency
    upstream: https://github.com/catboost/catboost
---

# CatBoost

Guidance for using CatBoost — Yandex's gradient boosting library — for **price-direction
classification**, **return regression**, and **multi-horizon time-series forecasting**.

This SKILL.md is a router: it tells you *when* to reach for CatBoost and *where* the detail
lives. Open the linked `references/` file for the actual code and parameter tables.

## Why CatBoost (vs. XGBoost / LightGBM)

Two distinguishing advantages:

1. **Best-in-class categorical handling** — accepts raw strings and learns ordered target
   statistics / CTR encodings internally; no preprocessing.
2. **First-class time-series support** — `has_time=True` plus the built-in `TimeSeries` CV fold
   type respect chronological order and avoid leaking future targets into past encodings.

It also offers symmetric/oblivious trees (fastest inference of the three), native multi-target
regression (`MultiRMSE`), and the strongest out-of-the-box defaults.

## When to use this skill

Use CatBoost when:

- More than ~20% of your features are **high-cardinality categoricals** (symbol, sector,
  exchange, regime label, hour-of-week buckets).
- Your data is **time-ordered** and you want ordered boosting + `has_time=True` to avoid target
  leakage in categorical encodings.
- You need **multi-target regression** (e.g., simultaneous return forecasts at 1h / 4h / 1d
  horizons) via `loss_function="MultiRMSE"`.
- You want **symmetric / oblivious trees** for very fast inference.
- You want **strong defaults** with minimal tuning.

Prefer **XGBoost** ([skill](../xgboost/SKILL.md)) when ecosystem breadth dominates and features
are mostly numeric. Prefer **LightGBM** ([skill](../lightgbm/SKILL.md)) when CPU training speed
is the top priority and features are mostly numeric.

## Installation

```bash
uv pip install catboost           # wheels ship with CPU + GPU (CUDA) support
# conda install -c conda-forge catboost   # alternative
```

GPU training works on NVIDIA CUDA GPUs out of the box. Verify with
`import catboost; print(catboost.__version__)`.

## Where the detail lives

- **[references/examples.md](references/examples.md)** — runnable patterns: classifier
  (direction), regressor (single-horizon returns), multi-horizon `MultiRMSE` forecast, and
  `type="TimeSeries"` cross-validation. All use time-respecting splits + `has_time=True`.
- **[references/api.md](references/api.md)** — the constructor-parameter table (the ~20 args that
  matter), `Pool` vs. array fitting, prediction-type access, and the Optuna tuning loop with
  `TimeSeriesSplit`.
- **[references/pitfalls-and-comparison.md](references/pitfalls-and-comparison.md)** — the six
  common pitfalls (forgetting `has_time`, `cat_features` timing, GPU depth-8 limit, `MultiRMSE`
  required defaults, CPU-speed tradeoff, don't-pre-encode-strings), the full CatBoost vs. XGBoost
  vs. LightGBM table, and the curated docs / papers / tutorials reference list.

## Minimal sanity check

```python
from catboost import CatBoostClassifier, Pool
clf = CatBoostClassifier(iterations=200, depth=6, has_time=True, verbose=False)
clf.fit(Pool(X_train, y_train, cat_features=cat_cols), eval_set=Pool(X_test, y_test, cat_features=cat_cols))
print(clf.get_best_iteration())
```

Then graduate to the full examples in `references/examples.md`.
