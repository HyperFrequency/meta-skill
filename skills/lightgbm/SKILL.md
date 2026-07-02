---
name: lightgbm
version: 0.1.0
description: >-
    LightGBM gradient-boosted decision trees for tabular price-direction classification and return regression. Use when the user asks to "train a LightGBM model", "predict direction with LGBM", "use LGBMClassifier / LGBMRegressor", needs the fastest GBM on CPU, or has hundreds–thousands of features. Covers the scikit-learn estimator API, leaf-wise growth, native categorical handling (`categorical_feature=`), `device_type="cuda"`/`"gpu"` training, the `early_stopping` callback, and Optuna tuning. NOT for: deep-learning / sequence models (use pytorch-lightning or transformers); heavy string-categorical or time-ordered data (prefer the catboost skill); broadest GPU / SHAP / ONNX / MLflow ecosystem needs or the most universal GPU build (prefer the xgboost skill); explaining a trained model's predictions (use the shap skill); datasets under ~5k rows where leaf-wise growth overfits (prefer xgboost / catboost).
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: MIT
metadata:
    skill-author: HyperFrequency
    upstream: https://github.com/microsoft/LightGBM
---

# LightGBM

## Overview

This skill provides guidance for using LightGBM — Microsoft's fast histogram-based GBM — for **price-direction classification** and **return regression** on tabular financial features. LightGBM grows trees **leaf-wise** (best-first) rather than level-wise, which usually produces lower loss in fewer trees but requires careful regularization to avoid overfitting on small datasets.

## When to Use This Skill

Use LightGBM when:

- You have **many features** (hundreds–thousands) and need the fastest training.
- You want **leaf-wise tree growth** for better fit at equal tree count.
- You are training on **CPU** (LightGBM is typically the fastest of the three on CPU).
- You have **integer-encoded categoricals** and want native handling without one-hot.
- You need **distributed / multi-machine** training (LightGBM has the most mature distributed mode).

Prefer **XGBoost** when ecosystem breadth (SHAP/ONNX/MLflow) matters most and you want the most universal GPU build. Prefer **CatBoost** when categoricals dominate or when you need time-series-aware ordering (`has_time`).

## Installation

```bash
# CPU build (default, works everywhere)
uv pip install lightgbm

# GPU build — pip wheels ship with OpenCL GPU support on most platforms
# CUDA-specific build requires source compile (see upstream docs)
uv pip install lightgbm

# Conda alternative
conda install -c conda-forge lightgbm
```

Verify:

```python
import lightgbm as lgb
print(lgb.__version__)
```

For GPU/CUDA training, the pip wheel works on most Linux/Windows systems with OpenCL drivers installed (`device_type="gpu"`). For CUDA-specific (`device_type="cuda"`, typically faster), build from source per the upstream `GPU-Tutorial`.

## Minimal Classifier Example — Direction Prediction

```python
# Predict next-bar direction (1 = up, 0 = down) from engineered OHLCV features.
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score

df = pd.read_parquet("features.parquet")
feature_cols = [c for c in df.columns if c not in ("timestamp", "target")]
cat_cols = [c for c in feature_cols if str(df[c].dtype) == "category"]
X, y = df[feature_cols], df["target"].astype(int)

# Time-respecting split: NO shuffling for financial data.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

clf = lgb.LGBMClassifier(
    boosting_type="gbdt",
    objective="binary",
    n_estimators=2000,
    learning_rate=0.03,
    num_leaves=63,                # leaf-wise grows fast; cap to control complexity
    max_depth=-1,                 # let num_leaves govern; -1 = no limit
    min_child_samples=20,
    subsample=0.8,
    subsample_freq=5,             # required for subsample < 1 to actually fire
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=0.1,
    random_state=42,
    n_jobs=-1,
    device_type="cpu",            # "gpu" (OpenCL) or "cuda" if you compiled that build
    verbose=-1,
)

clf.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    eval_metric="binary_logloss",
    categorical_feature=cat_cols or "auto",
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=0),   # silent
    ],
)

y_pred = clf.predict(X_test)
y_proba = clf.predict_proba(X_test)[:, 1]
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(f"AUC:      {roc_auc_score(y_test, y_proba):.4f}")
print(f"Best iter: {clf.best_iteration_}")
```

## Minimal Regressor Example — Return Prediction

```python
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, r2_score

reg = lgb.LGBMRegressor(
    boosting_type="gbdt",
    objective="regression",           # L2 / MSE; use "huber" or "regression_l1" for heavy tails
    n_estimators=2000,
    learning_rate=0.03,
    num_leaves=63,
    min_child_samples=20,
    subsample=0.8,
    subsample_freq=5,
    colsample_bytree=0.8,
    reg_alpha=0.1,
    reg_lambda=0.1,
    random_state=42,
    n_jobs=-1,
    verbose=-1,
)
reg.fit(
    X_train, y_train_returns,
    eval_set=[(X_test, y_test_returns)],
    eval_metric="rmse",
    callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
)
preds = reg.predict(X_test)
print(f"RMSE: {mean_squared_error(y_test_returns, preds, squared=False):.6f}")
print(f"R²:   {r2_score(y_test_returns, preds):.4f}")
```

## Key API Surface

### Constructor parameters that actually matter

| Parameter | Default | What it does |
|---|---|---|
| `boosting_type` | `"gbdt"` | `"gbdt"` (standard), `"dart"` (dropouts), `"goss"` (gradient sampling), `"rf"` (random forest). |
| `objective` | task-dependent | `"binary"`, `"multiclass"`, `"regression"`, `"regression_l1"`, `"huber"`, `"quantile"`. |
| `n_estimators` | 100 | Boosting rounds. Set 1000–5000 and rely on early stopping. |
| `learning_rate` | 0.1 | 0.01–0.05 typical for finance. |
| `num_leaves` | 31 | **Primary complexity knob** (leaf-wise growth). Keep `num_leaves < 2^max_depth`. 31–255 typical. |
| `max_depth` | -1 | -1 = no limit; let `num_leaves` govern. Set 4–10 to hard-cap. |
| `min_child_samples` (`min_data_in_leaf`) | 20 | Minimum samples per leaf. Raise to combat overfit. |
| `min_split_gain` (`min_gain_to_split`) | 0.0 | Minimum loss reduction to split. Effective regularizer. |
| `subsample` (`bagging_fraction`) | 1.0 | Row subsample per `subsample_freq` rounds. |
| `subsample_freq` (`bagging_freq`) | 0 | Set to 1–10 — required for `subsample < 1` to take effect. |
| `colsample_bytree` (`feature_fraction`) | 1.0 | Feature subsample per tree. |
| `reg_alpha` (`lambda_l1`) | 0.0 | L1 regularization. |
| `reg_lambda` (`lambda_l2`) | 0.0 | L2 regularization. |
| `categorical_feature` | `"auto"` | List of column names/indices to treat as categorical, or `"auto"` for pandas `category` dtype. |
| `device_type` (`device`) | `"cpu"` | `"cpu"`, `"gpu"` (OpenCL — broader compat), `"cuda"` (faster on NVIDIA, requires CUDA build). |
| `n_jobs` | -1 | -1 = all cores. |
| `random_state` | None | Set for reproducibility. |
| `verbose` | 1 | Set `-1` to silence the default log spam. |

### fit() signature — current API

```python
clf.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    eval_metric="binary_logloss",
    categorical_feature=cat_cols,         # or "auto" for pandas category dtype
    sample_weight=None,
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=100),
    ],
)
```

**Important — recent versions:** early stopping is a **callback**, not a constructor or `fit` kwarg. The old `early_stopping_rounds=` argument on `.fit()` was deprecated. Use `callbacks=[lgb.early_stopping(50)]`.

Access trained internals via `clf.best_iteration_`, `clf.feature_importances_`, `clf.booster_`.

## Hyperparameter Tuning — Optuna

Walk-forward (`TimeSeriesSplit`) Optuna objective over the full search space, plus the
`LightGBMPruningCallback` and `LightGBMTuner` options: see
[`references/tuning.md`](references/tuning.md).

## Common Pitfalls

1. **`num_leaves` is the primary knob, not `max_depth`** — LightGBM grows leaf-wise. With `max_depth=-1` and `num_leaves=255`, a tree can become wildly imbalanced and overfit. Rule of thumb: `num_leaves ≤ 2^max_depth - 1`. Tune `num_leaves` first; `max_depth` is mostly a safety cap.

2. **`subsample_freq=0` silently disables `subsample`** — setting `subsample=0.8` without `subsample_freq ≥ 1` does nothing. Always set both.

3. **Early stopping is a callback now** — older code with `clf.fit(..., early_stopping_rounds=50)` raises `TypeError` on current versions. Use `callbacks=[lgb.early_stopping(50)]`. Logging is also a callback: `lgb.log_evaluation(period=N)`; pass `period=0` for silence.

4. **Categorical encoding must be integer** — LightGBM accepts integer-encoded categoricals (or pandas `category` dtype that it converts internally). Raw string columns raise. Encode with `pd.Categorical` or sklearn `OrdinalEncoder` first. Setting `categorical_feature="auto"` only picks up columns already in `category` dtype.

5. **Missing-value semantics** — `use_missing=True` (default) treats NaN as a separate direction at each split. With `zero_as_missing=True`, zeros are *also* treated as missing — useful for sparse one-hot data but dangerous for OHLCV features where zero is a real value.

6. **Small data + leaf-wise growth = overfit** — under ~5k rows, LightGBM can fit noise faster than XGBoost. Use small `num_leaves` (≤31), large `min_child_samples` (≥50), and aggressive `min_split_gain`. Or just pick XGBoost / CatBoost for small datasets.

## Cross-Comparison & Sibling Skills

Full LightGBM vs. XGBoost vs. CatBoost decision table (tree growth, CPU speed,
categorical handling, GPU builds, distributed training, time-series support) plus when
to reach for a sibling: see [`references/comparison.md`](references/comparison.md).

Quick routing:
- **XGBoost** (`../xgboost/SKILL.md`) — broadest ecosystem (SHAP/ONNX/MLflow), most universal GPU build.
- **CatBoost** (`../catboost/SKILL.md`) — strongest defaults, best categorical handling, `has_time` ordering.

## References

Upstream docs, deep-dive pages, adjacent libraries, academic papers, and the
last-cross-checked provenance are collected in
[`references/resources.md`](references/resources.md).
