# CatBoost — Worked Examples

Runnable patterns for price-direction classification, return regression, and multi-horizon
forecasting. All use **time-respecting splits** (no shuffling) and `has_time=True` — mandatory
for financial / sequential data.

## Classifier — next-bar direction prediction

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

## Regressor — single-horizon returns

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

## Multi-horizon forecast — `MultiRMSE`

CatBoost natively supports vector targets. Forecast multiple horizons (e.g., 1h, 4h, 1d returns)
jointly — the trees share structure and the model learns horizon correlations.

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

## Time-series cross-validation — `TimeSeries` fold type

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

`type="TimeSeries"` builds expanding-window folds in chronological order — the exact pattern
needed for financial backtesting, and it reduces the standard deviation of validation loss
compared to random K-fold on temporal data.
