---
name: xgboost
description: XGBoost gradient-boosted decision trees for tabular price-direction classification and return regression. Use when the user asks to "train an XGBoost model", "predict direction with XGBoost", "boost trees on OHLCV features", "use XGBClassifier / XGBRegressor", or wants a battle-tested baseline before reaching for deep learning. Covers the scikit-learn estimator API, native categorical support (`enable_categorical=True`), GPU training (`device="cuda"`), early stopping, and Optuna tuning.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: Apache-2.0
metadata:
    skill-author: HyperFrequency
    upstream: https://github.com/dmlc/xgboost
---

# XGBoost

## Overview

This skill provides guidance for using XGBoost — the original optimized distributed gradient boosting library — for **price-direction classification** (binary up/down, multi-class regime) and **return regression** on tabular financial features. XGBoost is the default choice when you want a well-understood, broadly-supported baseline with the largest ecosystem (SHAP, MLflow, ONNX, treelite all work first-class).

## When to Use This Skill

Use XGBoost when:

- You want a **strong tabular baseline** before considering LightGBM or CatBoost.
- You need **broad ecosystem support** — every interpretability / serving / monitoring tool integrates with XGBoost first.
- You have **mostly numeric features** with a small/medium number of categoricals.
- You need **GPU training** that works on a wider range of platforms than LightGBM's CUDA build.
- You want **deterministic, well-documented behavior** for missing values (XGBoost picks the optimal default direction per split).

Prefer **LightGBM** when training speed dominates and you have many features. Prefer **CatBoost** when more than ~30% of features are high-cardinality categoricals or when you need built-in time-series ordering (`has_time`).

## Installation

```bash
# CPU + GPU build (Linux x86_64/aarch64, Windows). macOS is CPU-only.
uv pip install xgboost

# CPU-only (smaller wheel, useful in slim Docker images)
uv pip install xgboost-cpu

# Conda alternative (detects GPU automatically)
conda install -c conda-forge py-xgboost
```

GPU usage requires a CUDA-capable NVIDIA GPU and a recent NVIDIA driver. No extra flag is needed at install time — the same wheel ships CPU + GPU kernels. Verify with:

```python
import xgboost as xgb
print(xgb.__version__)              # e.g. "2.1.x" or "3.x"
print(xgb.build_info())             # confirms CUDA, federated, etc.
```

## Minimal Classifier Example — Direction Prediction

```python
# Predict next-bar direction (1 = up, 0 = down) from engineered OHLCV features.
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

# Replace with your feature pipeline. y must be {0, 1}.
df = pd.read_parquet("features.parquet")
feature_cols = [c for c in df.columns if c not in ("timestamp", "target")]
X, y = df[feature_cols], df["target"].astype(int)

# Time-respecting split: NO shuffling for financial data.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

clf = xgb.XGBClassifier(
    n_estimators=2000,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    tree_method="hist",            # required for early_stopping + categorical + GPU
    early_stopping_rounds=50,
    eval_metric="logloss",
    device="cuda",                 # set "cpu" if no GPU; deprecated: gpu_id/predictor
    enable_categorical=True,       # pandas 'category' dtype handled natively
    random_state=42,
    n_jobs=-1,
)
clf.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_pred = clf.predict(X_test)
y_proba = clf.predict_proba(X_test)[:, 1]
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(f"AUC:      {roc_auc_score(y_test, y_proba):.4f}")
print(f"Best iter: {clf.best_iteration}")
```

## Minimal Regressor Example — Return Prediction

```python
import xgboost as xgb
from sklearn.metrics import mean_squared_error, r2_score

reg = xgb.XGBRegressor(
    n_estimators=2000,
    max_depth=6,
    learning_rate=0.03,
    subsample=0.8,
    colsample_bytree=0.8,
    tree_method="hist",
    early_stopping_rounds=50,
    eval_metric="rmse",
    objective="reg:squarederror",   # or "reg:pseudohubererror" for heavy tails
    device="cuda",
    enable_categorical=True,
    random_state=42,
)
reg.fit(X_train, y_train_returns, eval_set=[(X_test, y_test_returns)], verbose=False)
preds = reg.predict(X_test)
print(f"RMSE: {mean_squared_error(y_test_returns, preds, squared=False):.6f}")
print(f"R²:   {r2_score(y_test_returns, preds):.4f}")
```

## Key API Surface

### Constructor parameters that actually matter

| Parameter | Default | What it does |
|---|---|---|
| `n_estimators` | 100 | Max boosting rounds. Set high (1000–5000) and rely on `early_stopping_rounds`. |
| `learning_rate` (`eta`) | 0.3 | Step size shrinkage. 0.01–0.1 is typical for finance. |
| `max_depth` | 6 | Tree depth. 3–8 for most tabular work; deeper overfits. |
| `min_child_weight` | 1 | Minimum sum of instance weight in a child. Raise to combat overfit. |
| `gamma` | 0 | Minimum loss reduction for split. Effective regularizer. |
| `subsample` | 1.0 | Row subsample per tree. 0.7–0.9 typical. |
| `colsample_bytree` | 1.0 | Feature subsample per tree. 0.5–0.9 typical. |
| `reg_alpha` | 0 | L1 regularization. |
| `reg_lambda` | 1 | L2 regularization. |
| `tree_method` | "auto" | Use `"hist"` for speed + categorical + GPU support. `"exact"` only for very small data. |
| `device` | "cpu" | `"cuda"` for GPU. **Replaces deprecated** `gpu_id`, `predictor="gpu_predictor"`. |
| `enable_categorical` | False | Set `True` to handle pandas `category` dtype natively. Requires `tree_method="hist"` or `"approx"`. |
| `max_cat_to_onehot` | 4 | Categories ≤ this use one-hot; larger use partition (Fisher) algorithm. |
| `early_stopping_rounds` | None | Stop if eval metric stops improving for N rounds. Pass `eval_set` to `.fit()`. |
| `eval_metric` | objective-dependent | `"logloss"`, `"auc"`, `"rmse"`, `"mae"`, `"merror"`. |
| `objective` | task-dependent | `"binary:logistic"`, `"multi:softprob"`, `"reg:squarederror"`, `"reg:pseudohubererror"`. |
| `n_jobs` | 0 | `-1` = all cores. |
| `random_state` | None | Set for reproducibility. |

### fit() signature

```python
clf.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],   # required when early_stopping_rounds is set
    sample_weight=None,
    verbose=False,
)
```

Access trained internals via `clf.best_iteration`, `clf.feature_importances_`, `clf.get_booster()`.

## Hyperparameter Tuning — Optuna

```python
import optuna
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import log_loss

def objective(trial):
    params = {
        "n_estimators": 3000,
        "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.2, log=True),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 20.0),
        "gamma": trial.suggest_float("gamma", 1e-8, 5.0, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        "tree_method": "hist",
        "device": "cuda",
        "early_stopping_rounds": 50,
        "eval_metric": "logloss",
        "random_state": 42,
    }
    cv = TimeSeriesSplit(n_splits=5)
    scores = []
    for tr, va in cv.split(X):
        clf = xgb.XGBClassifier(**params)
        clf.fit(X.iloc[tr], y.iloc[tr], eval_set=[(X.iloc[va], y.iloc[va])], verbose=False)
        scores.append(log_loss(y.iloc[va], clf.predict_proba(X.iloc[va])[:, 1]))
    return float(np.mean(scores))

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=50, show_progress_bar=True)
print(study.best_params)
```

Built-in CV alternative — `xgb.cv()` works on the low-level `DMatrix` API and returns per-fold metric history; use it when you do not need per-trial parallelism.

## Common Pitfalls

1. **`n_estimators` vs. `early_stopping_rounds`** — when early stopping fires, predictions automatically use `best_iteration`. Don't manually slice trees. With `learning_rate=0.03` you typically want `n_estimators ≥ 2000` so early stopping has room to find the optimum.

2. **`eval_set` is required for early stopping** — `fit(X, y)` alone with `early_stopping_rounds` set raises. Always pass `eval_set=[(X_val, y_val)]`.

3. **Categorical handling differs from LightGBM/CatBoost** — XGBoost requires `enable_categorical=True` **and** `tree_method` in `{"hist", "approx"}` **and** input columns in pandas `category` dtype. It does **not** accept string columns directly. Save models as JSON/UBJSON (`save_model("m.json")`) — pickling loses categorical metadata.

4. **Missing values are part of the algorithm** — XGBoost learns the optimal default direction at each split. Don't impute NaNs upfront; pass them through. Imputing with means/zeros often hurts.

5. **GPU has overhead on small data** — `device="cuda"` becomes a win above ~10k rows × ~50 features. Below that, `device="cpu"` with `n_jobs=-1` is often faster.

6. **`shuffle=False` for time series** — `train_test_split` defaults to shuffling. For financial data use `shuffle=False` or `TimeSeriesSplit` for CV; otherwise future leaks into training.

## Cross-Comparison: XGBoost vs. LightGBM vs. CatBoost

| Dimension | XGBoost | LightGBM | CatBoost |
|---|---|---|---|
| **Categorical handling** | Native via `enable_categorical=True` (pandas category dtype only) | Native via `categorical_feature=` (int-encoded) | Best-in-class — native strings, target/CTR encoding, `cat_features=` |
| **Speed (CPU, ~1M rows)** | Fast (hist) | Fastest | Slowest of the three |
| **GPU support** | Broadest (CUDA on Linux/Win x86_64+aarch64) | CUDA + OpenCL; CUDA build less universal | Strong CUDA, includes multi-GPU |
| **Missing values** | Learned per split (best default direction) | Learned per split (`use_missing=true`) | Treated as separate category / value |
| **Ecosystem (SHAP, ONNX, MLflow, treelite)** | Best | Strong | Strong |
| **Time-series specific** | None built-in | None built-in | `has_time=True`, `TimeSeries` CV fold type |
| **Default win condition** | Broad baseline, mature ecosystem | Many features + need speed | Heavy categorical / time-ordered data |

## References

### Primary library
- [dmlc/xgboost](https://github.com/dmlc/xgboost) — upstream repo (issues, releases, JVM / R / Python / Julia bindings live here)
- [XGBoost stable docs](https://xgboost.readthedocs.io/en/stable/) — cross-checked against the `stable` channel (`xgboost>=2.0` series)
- [Installation guide](https://xgboost.readthedocs.io/en/stable/install.html) — covers CPU-only, CUDA, JVM, distributed (Dask/Spark/Ray) wheels
- [`demo/` directory](https://github.com/dmlc/xgboost/tree/master/demo) — runnable scripts mirroring tutorial pages
- [Release notes / migration](https://xgboost.readthedocs.io/en/stable/changes.html) — read this before pinning across a major; 2.0 made categorical/GPU defaults sticky

### Deep-dive docs (specific pages worth bookmarking)
- [Python API reference](https://xgboost.readthedocs.io/en/stable/python/python_api.html) — `DMatrix`, `train`, `Booster.predict(iteration_range=...)`; the source of truth for keyword arguments
- [Sklearn estimator interface](https://xgboost.readthedocs.io/en/stable/python/sklearn_estimator.html) — `XGBClassifier`, `XGBRegressor`, `XGBRanker` — the API most production code uses
- [Parameters reference](https://xgboost.readthedocs.io/en/stable/parameter.html) — exhaustive list of `tree_method`, `device`, `objective`, regularisation, sampling params
- [Categorical Data tutorial](https://xgboost.readthedocs.io/en/stable/tutorials/categorical.html) — `enable_categorical=True`, `max_cat_to_onehot`, `max_cat_threshold`; the difference between this and target-encoding-yourself matters
- [GPU Support](https://xgboost.readthedocs.io/en/stable/gpu/index.html) — `device="cuda"` semantics + multi-GPU via Dask
- [Distributed XGBoost (Dask / Spark / Ray)](https://xgboost.readthedocs.io/en/stable/tutorials/index.html) — when single-machine isn't enough
- [Missing Values](https://xgboost.readthedocs.io/en/stable/faq.html#how-to-deal-with-missing-values) — how XGBoost learns the best split direction for NaNs by default
- [Custom Objective and Evaluation Metric](https://xgboost.readthedocs.io/en/stable/tutorials/custom_metric_obj.html) — required reading if you need quantile / asymmetric loss for quant
- [Saving / loading models](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html) — JSON/UBJSON vs binary; only JSON/UBJSON survives version bumps
- [SHAP integration](https://xgboost.readthedocs.io/en/stable/tutorials/feature_interaction_constraint.html) — `pred_contribs=True` on `predict` for built-in TreeSHAP

### Adjacent / alternative libraries
- `lightgbm` — see [`lightgbm` skill](../lightgbm/SKILL.md) — typically faster on dense numeric features; comparable accuracy
- `catboost` — see [`catboost` skill](../catboost/SKILL.md) — strongest defaults + best categorical handling
- [scikit-learn `GradientBoostingClassifier` / `HistGradientBoostingClassifier`](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting) — pure-sklearn baseline with no extra install
- [`treelite`](https://github.com/dmlc/treelite) — compile XGBoost trees to C / shared lib for low-latency inference

### Academic papers
- Chen, T. & Guestrin, C. (2016). "XGBoost: A Scalable Tree Boosting System." *KDD '16*. [arXiv:1603.02754](https://arxiv.org/abs/1603.02754) — the original paper; covers the sparsity-aware split + weighted-quantile sketch + cache-aware block structure that defined the library
- Friedman, J. H. (2001). "Greedy Function Approximation: A Gradient Boosting Machine." *Annals of Statistics* 29(5), 1189–1232. [doi:10.1214/aos/1013203451](https://doi.org/10.1214/aos/1013203451) — the GBM foundation XGBoost extends

### Tutorials & write-ups
- [XGBoost intro from the docs](https://xgboost.readthedocs.io/en/stable/tutorials/model.html) — concise mathematical intro; the second-order Taylor expansion that motivates the regularisation term lives here
- [Tianqi Chen's talk slides (xgboost.ai)](https://xgboost.ai/) — author's own positioning of the algorithm

### Last cross-checked
2026-05-20 — via Context7 `/dmlc/xgboost` (heaviest coverage), upstream docs at `xgboost.readthedocs.io/en/stable/`; Auggie not indexed for this repo.
