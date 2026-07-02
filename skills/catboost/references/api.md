# CatBoost — Key API Surface

## Constructor parameters that actually matter

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
| `bootstrap_type` | auto | `"Bayesian"`, `"Bernoulli"`, `"MVS"`, `"No"`. `"Bayesian"` is the default for most losses; required for `MultiRMSE` patterns. |
| `subsample` | varies | Used with Bernoulli/MVS bootstrap. |
| `random_strength` | 1.0 | Score perturbation for split selection (regularizer). |
| `border_count` (`max_bin`) | 254 (CPU) / 128 (GPU) | Number of splits per feature; lower = faster. |
| `boosting_type` | auto | `"Ordered"` (default on small data — slower but less leakage) or `"Plain"` (default on large data). |
| `random_seed` | None | Set for reproducibility. |
| `verbose` | True | Pass `False` or an integer period to control logging. |

## Fitting via `Pool` (preferred) or arrays

```python
# Pool is preferred — it bundles X, y, weights, baseline, cat_features, text_features in one object.
from catboost import Pool
train_pool = Pool(X_train, y_train, cat_features=cat_cols, weight=sample_weight)
eval_pool  = Pool(X_test,  y_test,  cat_features=cat_cols)
model.fit(train_pool, eval_set=eval_pool)

# Or pass arrays + cat_features positionally / as kwarg
model.fit(X_train, y_train, cat_features=cat_cols, eval_set=(X_test, y_test))
```

Access: `model.get_best_iteration()`, `model.get_feature_importance()`,
`model.predict(X, prediction_type="Class"|"Probability"|"RawFormulaVal")`.

## Hyperparameter tuning — Optuna

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

CatBoost also ships `model.grid_search(...)` and `model.randomized_search(...)` as built-in
alternatives.
