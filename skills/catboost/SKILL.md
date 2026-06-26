---
name: catboost
description: CatBoost gradient-boosted decision trees for tabular price-direction classification and time-series return prediction. Use when the user asks to "train a CatBoost model", "predict direction with CatBoost", "use CatBoostClassifier / CatBoostRegressor", has heavy categorical features (symbol, exchange, regime), or needs time-ordered training via `has_time=True` and the `TimeSeries` CV fold type. Covers the scikit-learn-style API, native string categoricals + CTR/target encoding, multi-target return forecasting with `loss_function="MultiRMSE"`, GPU training (`task_type="GPU"`), and Optuna tuning.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: Apache-2.0
metadata:
    skill-author: HyperFrequency
    upstream: https://github.com/catboost/catboost
---

# CatBoost

## Overview

This skill provides guidance for using CatBoost — Yandex's gradient boosting library — for **price-direction classification**, **return regression**, and **multi-horizon time-series forecasting**. CatBoost's two distinguishing advantages over XGBoost / LightGBM are: (1) **best-in-class categorical handling** (it accepts raw strings and learns ordered target statistics / CTR encodings internally — no preprocessing); and (2) **first-class time-series support** via `has_time=True` and the built-in `TimeSeries` CV fold type, which respects chronological order.

## When to Use This Skill

Use CatBoost when:

- More than ~20% of your features are **high-cardinality categoricals** (symbol, sector, exchange, regime label, hour-of-week buckets).
- Your data is **time-ordered** and you want CatBoost's ordered boosting + `has_time=True` to avoid target leakage in categorical encodings.
- You need **multi-target regression** (e.g., simultaneous return forecasts at 1h / 4h / 1d horizons) via `loss_function="MultiRMSE"`.
- You want **symmetric / oblivious trees** for very fast inference (CatBoost trees are uniform, which makes serving cheap).
- You want **strong defaults** — CatBoost typically performs well with minimal tuning.

Prefer **XGBoost** when ecosystem breadth dominates and features are mostly numeric. Prefer **LightGBM** when training speed on CPU is the top priority and features are mostly numeric.

## Installation

```bash
# Pip — wheels ship with CPU + GPU (CUDA) support
uv pip install catboost

# Conda alternative
conda install -c conda-forge catboost
```

GPU training works on NVIDIA CUDA-capable GPUs out of the box. Verify:

```python
import catboost
print(catboost.__version__)
```

## Minimal Classifier Example — Direction Prediction

```python
# Predict next-bar direction (1 = up, 0 = down) with native string categoricals.
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import accuracy_score, roc_auc_score

df = pd.read_parquet("features.parquet").sort_values("timestamp")
feature_cols = [c for c in df.columns if c not in ("timestamp", "target")]
cat_cols = [c for c in feature_cols if df[c].dtype == object or str(df[c].dtype) == "category"]
X, y = df[feature_cols], df["target"].astype(int)

# Time-respecting split — NO shuffling for financial data.
split = int(len(df) * 0.8)
X_train, X_test = X.iloc[:split], X.iloc[split:]
y_train, y_test = y.iloc[:split], y.iloc[split:]

train_pool = Pool(X_train, y_train, cat_features=cat_cols)
test_pool  = Pool(X_test,  y_test,  cat_features=cat_cols)

clf = CatBoostClassifier(
    iterations=2000,
    learning_rate=0.03,
    depth=6,
    l2_leaf_reg=3.0,
    loss_function="Logloss",     # or "MultiClass" for multi-regime
    eval_metric="AUC",
    early_stopping_rounds=50,
    task_type="GPU",             # "CPU" if no GPU
    devices="0",                 # "0:1" for multi-GPU
    has_time=True,               # respect row order; disable shuffling of permutations
    random_seed=42,
    verbose=False,
)
clf.fit(train_pool, eval_set=test_pool)

y_pred = clf.predict(X_test)
y_proba = clf.predict_proba(X_test)[:, 1]
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
print(f"AUC:      {roc_auc_score(y_test, y_proba):.4f}")
print(f"Best iter: {clf.get_best_iteration()}")
```

## Minimal Regressor Example — Single-Horizon Returns

```python
from catboost import CatBoostRegressor, Pool

reg = CatBoostRegressor(
    iterations=2000,
    learning_rate=0.03,
    depth=6,
    l2_leaf_reg=3.0,
    loss_function="RMSE",        # or "MAE", "Huber:delta=1.0", "Quantile:alpha=0.5"
    eval_metric="RMSE",
    early_stopping_rounds=50,
    task_type="GPU",
    has_time=True,
    random_seed=42,
    verbose=False,
)
reg.fit(
    Pool(X_train, y_train_returns, cat_features=cat_cols),
    eval_set=Pool(X_test, y_test_returns, cat_features=cat_cols),
)
preds = reg.predict(X_test)
```

## Time-Series Example — Multi-Horizon Forecast with `MultiRMSE`

CatBoost natively supports vector targets. Use it to forecast multiple horizons (e.g., 1h, 4h, 1d returns) jointly — the trees share structure and the model learns horizon correlations.

```python
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool, cv

# y is shape (n_samples, n_horizons) — e.g., next-bar, +4-bar, +24-bar returns.
horizons = [1, 4, 24]
y_multi = np.column_stack([df[f"ret_{h}"].values for h in horizons])

split = int(len(df) * 0.8)
X_train, X_test = X.iloc[:split], X.iloc[split:]
y_train, y_test = y_multi[:split], y_multi[split:]

model = CatBoostRegressor(
    iterations=2000,
    learning_rate=0.03,
    depth=6,
    loss_function="MultiRMSE",      # or "MultiRMSEWithMissingValues"
    eval_metric="MultiRMSE",
    bootstrap_type="Bayesian",
    boost_from_average=False,
    leaf_estimation_iterations=1,
    leaf_estimation_method="Gradient",
    early_stopping_rounds=50,
    task_type="GPU",
    has_time=True,
    random_seed=42,
    verbose=False,
)
model.fit(
    Pool(X_train, y_train, cat_features=cat_cols),
    eval_set=Pool(X_test, y_test, cat_features=cat_cols),
)
preds = model.predict(X_test)        # shape (n_test, len(horizons))
```

### Time-series cross-validation — `TimeSeries` fold type

```python
from catboost import cv, Pool

params = {
    "iterations": 2000,
    "learning_rate": 0.03,
    "depth": 6,
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "early_stopping_rounds": 50,
    "task_type": "CPU",
    "has_time": True,
    "verbose": False,
}
cv_results = cv(
    pool=Pool(X, y, cat_features=cat_cols),
    params=params,
    fold_count=5,
    type="TimeSeries",       # train on folds [0..k], validate on fold k+1 — no future leak
    shuffle=False,           # required for TimeSeries
    plot=False,
)
print(cv_results.tail())
```

`type="TimeSeries"` builds expanding-window folds in chronological order — the exact pattern needed for financial backtesting and reduces the standard deviation of validation loss compared to random K-fold on temporal data.

## Key API Surface

### Constructor parameters that actually matter

| Parameter | Default | What it does |
|---|---|---|
| `iterations` (`num_boost_round`) | 1000 | Max boosting rounds. Set high (1000–5000) and rely on `early_stopping_rounds`. |
| `learning_rate` | auto | If unset, CatBoost picks a sensible default from data size. 0.01–0.05 typical for tuning. |
| `depth` (`max_depth`) | 6 | Tree depth. **Max 16 on CPU, 8 on GPU.** 4–8 typical. |
| `l2_leaf_reg` | 3.0 | L2 regularization on leaf values. Primary regularizer. 1–10 typical. |
| `cat_features` | None | Indices or names of categorical columns. Pass via `Pool(...)` or to `fit(...)`. |
| `text_features` | None | Indices/names of text columns (CatBoost will tokenize + featurize). |
| `embedding_features` | None | Indices/names of pre-computed embedding columns (each value is a vector). |
| `loss_function` | task-default | `"Logloss"`, `"MultiClass"`, `"RMSE"`, `"MAE"`, `"Huber:delta=1"`, `"Quantile:alpha=0.5"`, `"MultiRMSE"`, `"MultiRMSEWithMissingValues"`. |
| `eval_metric` | matches loss | `"AUC"`, `"Logloss"`, `"Accuracy"`, `"RMSE"`, `"MAE"`, `"MAPE"`. |
| `early_stopping_rounds` | None | Stop if eval metric stops improving for N rounds. Requires `eval_set`. |
| `task_type` | `"CPU"` | `"CPU"` or `"GPU"`. |
| `devices` | `None` | GPU device string, e.g., `"0"`, `"0:1"`, `"0-3"`. |
| `has_time` | False | **Set True for time-ordered data.** Disables permutation shuffling so ordered statistics respect chronology. |
| `bootstrap_type` | auto | `"Bayesian"`, `"Bernoulli"`, `"MVS"`, `"No"`. `"Bayesian"` is the default for most losses; required for `MultiRMSE` patterns above. |
| `subsample` | varies | Used with Bernoulli/MVS bootstrap. |
| `random_strength` | 1.0 | Score perturbation for split selection (regularizer). |
| `border_count` (`max_bin`) | 254 (CPU) / 128 (GPU) | Number of splits per feature; lower = faster. |
| `boosting_type` | auto | `"Ordered"` (default on small data — slower but less leakage) or `"Plain"` (default on large data). |
| `random_seed` | None | Set for reproducibility. |
| `verbose` | True | Pass `False` or an integer period to control logging. |

### Fitting via `Pool` (preferred) or arrays

```python
# Pool is preferred — it bundles X, y, weights, baseline, cat_features, text_features in one object.
from catboost import Pool
train_pool = Pool(X_train, y_train, cat_features=cat_cols, weight=sample_weight)
eval_pool  = Pool(X_test,  y_test,  cat_features=cat_cols)
model.fit(train_pool, eval_set=eval_pool)

# Or pass arrays + cat_features positionally / as kwarg
model.fit(X_train, y_train, cat_features=cat_cols, eval_set=(X_test, y_test))
```

Access: `model.get_best_iteration()`, `model.get_feature_importance()`, `model.predict(X, prediction_type="Class"|"Probability"|"RawFormulaVal")`.

## Hyperparameter Tuning — Optuna

```python
import optuna
import numpy as np
from catboost import CatBoostClassifier, Pool
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import log_loss

def objective(trial):
    params = dict(
        iterations=3000,
        learning_rate=trial.suggest_float("learning_rate", 1e-3, 0.2, log=True),
        depth=trial.suggest_int("depth", 4, 10),
        l2_leaf_reg=trial.suggest_float("l2_leaf_reg", 1.0, 20.0, log=True),
        random_strength=trial.suggest_float("random_strength", 1e-3, 10.0, log=True),
        bagging_temperature=trial.suggest_float("bagging_temperature", 0.0, 1.0),
        border_count=trial.suggest_int("border_count", 32, 254),
        loss_function="Logloss",
        eval_metric="Logloss",
        early_stopping_rounds=50,
        task_type="GPU",
        has_time=True,
        random_seed=42,
        verbose=False,
    )
    cv = TimeSeriesSplit(n_splits=5)
    scores = []
    for tr, va in cv.split(X):
        clf = CatBoostClassifier(**params)
        clf.fit(
            Pool(X.iloc[tr], y.iloc[tr], cat_features=cat_cols),
            eval_set=Pool(X.iloc[va], y.iloc[va], cat_features=cat_cols),
        )
        scores.append(log_loss(y.iloc[va], clf.predict_proba(X.iloc[va])[:, 1]))
    return float(np.mean(scores))

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=40, show_progress_bar=True)
print(study.best_params)
```

CatBoost also ships `model.grid_search(...)` and `model.randomized_search(...)` if you want a built-in alternative.

## Common Pitfalls

1. **Forgetting `has_time=True` on time-series data** — by default CatBoost generates random permutations to compute ordered target statistics for categoricals. On chronological data this can leak future targets into past encodings. Always set `has_time=True` for financial / sequential data; this fixes the permutation to the row order.

2. **`cat_features` must be specified at `Pool`/`fit` time, not later** — CatBoost computes statistics over the categorical columns during model construction. Passing them only at `predict` time errors out. Either build a `Pool` with `cat_features=`, or pass to `fit(..., cat_features=cat_cols)`.

3. **GPU depth limit is 8** — `depth > 8` with `task_type="GPU"` either errors or silently caps. If you need deeper trees, fall back to `task_type="CPU"` (max depth 16).

4. **`MultiRMSE` requires specific defaults** — the upstream tutorial uses `bootstrap_type="Bayesian"`, `boost_from_average=False`, `leaf_estimation_iterations=1`, `leaf_estimation_method="Gradient"`. Deviating (e.g., Bernoulli bootstrap) can fail or converge poorly.

5. **CatBoost is slower than LightGBM/XGBoost on small CPU jobs** — but its inference is fast (oblivious trees). If train time dominates and you have no categoricals, LightGBM/XGBoost are better choices. If inference latency dominates, CatBoost often wins.

6. **String categoricals are first-class — don't pre-encode** — passing one-hot or label-encoded categoricals to CatBoost *and* listing them in `cat_features` confuses it. Either pass raw strings/ints and list them in `cat_features`, or pre-encode and **omit** them from `cat_features`. The former usually performs better thanks to ordered target encoding.

## Cross-Comparison: CatBoost vs. XGBoost vs. LightGBM

| Dimension | CatBoost | XGBoost | LightGBM |
|---|---|---|---|
| **Categorical handling** | **Best.** Native strings, ordered target / CTR encoding, no preprocessing | Native via `enable_categorical=True` (pandas category dtype only) | Native via `categorical_feature=` (int-encoded) |
| **Time-series awareness** | **`has_time=True`, `type="TimeSeries"` CV** | None built-in | None built-in |
| **Multi-target regression** | **Native — `MultiRMSE`, `MultiRMSEWithMissingValues`** | Wrap with `MultiOutputRegressor` | Wrap with `MultiOutputRegressor` |
| **Speed (CPU train)** | Slowest | Fast | Fastest |
| **Inference speed** | **Fastest** (symmetric/oblivious trees) | Fast | Fast |
| **GPU support** | Strong CUDA, multi-GPU | Broadest CUDA support | CUDA (source build) or OpenCL |
| **Defaults** | **Strongest** — works well untuned | Good | Aggressive — needs tuning on small data |
| **Tree structure** | Symmetric / oblivious | Asymmetric, level-wise | Asymmetric, leaf-wise |
| **Default win condition** | Heavy categoricals, time-ordered data, low-tuning budget | Broad baseline + ecosystem | Many numeric features + speed-critical |

## References

### Primary library
- [catboost/catboost](https://github.com/catboost/catboost) — upstream repo (issues, releases, C++ / Python / R / Java / .NET / CLI all live here)
- [CatBoost docs](https://catboost.ai/en/docs/) — cross-checked against the current release
- [Installation](https://catboost.ai/en/docs/concepts/python-installation) — pip / conda; GPU is included in the standard wheel
- [`tutorials/` directory](https://github.com/catboost/catboost/tree/master/catboost/tutorials) — runnable notebooks (categoricals, custom-loss, CV, ranking, uncertainty)
- [Release notes](https://github.com/catboost/catboost/releases) — read before pinning across majors

### Deep-dive docs (specific pages worth bookmarking)
- [Python usage examples](https://catboost.ai/en/docs/concepts/python-usages-examples) — minimal `CatBoostClassifier` / `Regressor` / `Ranker` patterns
- [Training parameters](https://catboost.ai/en/docs/references/training-parameters) — exhaustive parameter list (iterations, learning_rate, l2_leaf_reg, bootstrap_type, etc.)
- [`Pool` class](https://catboost.ai/en/docs/concepts/python-reference_pool) — wraps `data + cat_features + text_features + embedding_features`; this is *the* class to learn before anything else
- [Categorical features](https://catboost.ai/en/docs/concepts/algorithm-main-stages_cat-to-numberic) — ordered target statistics, the headline algorithmic feature
- [Time-series CV (`has_time=True`)](https://catboost.ai/en/docs/concepts/python-reference_cv) — chronological CV folds, the only correct evaluation mode for price data
- [GPU training](https://catboost.ai/en/docs/features/training-on-gpu) — `task_type="GPU"` + `devices`; CatBoost has strong multi-GPU
- [Custom loss / metric](https://catboost.ai/en/docs/concepts/python-usages-examples#user-defined-loss-function) — required for asymmetric or quantile loss
- [SHAP values](https://catboost.ai/en/docs/concepts/shap-values) — built-in TreeSHAP via `get_feature_importance(type="ShapValues")`
- [Uncertainty quantification](https://catboost.ai/en/docs/references/uncertainty) — the `RMSEWithUncertainty` + virtual ensembles route; useful for risk-aware position sizing
- [Model export to native code (CoreML / ONNX / C++ / Python)](https://catboost.ai/en/docs/concepts/python-reference_catboost_save_model) — covers low-latency inference patterns

### Adjacent / alternative libraries
- `xgboost` — see [`xgboost` skill](../xgboost/SKILL.md) — broader ecosystem; needed when CatBoost's narrower bindings hurt
- `lightgbm` — see [`lightgbm` skill](../lightgbm/SKILL.md) — typically faster training on dense numeric features
- [scikit-learn `HistGradientBoostingClassifier`](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting) — pure-sklearn baseline; no native categorical handling
- [`treelite`](https://github.com/dmlc/treelite) — compile any of XGB/LGBM/CatBoost trees to a single inference DLL

### Academic papers
- Prokhorenkova, L., Gusev, G., Vorobev, A., Dorogush, A. V., Gulin, A. (2018). "CatBoost: unbiased boosting with categorical features." *NeurIPS 2018*. [arXiv:1706.09516](https://arxiv.org/abs/1706.09516) — the original paper; introduces *ordered boosting* (the permutation-driven fix to target leakage) and the symmetric/oblivious tree predictor
- Dorogush, A. V., Ershov, V., Gulin, A. (2018). "CatBoost: gradient boosting with categorical features support." [arXiv:1810.11363](https://arxiv.org/abs/1810.11363) — companion workshop paper, focuses on categorical encodings

### Tutorials & write-ups
- [Yandex official CatBoost intro](https://catboost.ai/en/docs/concepts/about) — author-team positioning of the algorithm
- [Symmetric/oblivious trees explainer](https://catboost.ai/en/docs/concepts/algorithm-main-stages_choosing-tree-structure) — why CatBoost is the fastest at inference time among the three

### Last cross-checked
2026-05-20 — via Context7 `/catboost/catboost` (19,893 snippets — heaviest coverage of the three boosters) + upstream docs at `catboost.ai/en/docs/`; Auggie not indexed.
