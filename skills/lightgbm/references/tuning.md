# LightGBM Hyperparameter Tuning — Optuna

Use walk-forward (`TimeSeriesSplit`) folds for financial data — never random K-fold,
which leaks future information across the split boundary.

```python
import optuna
import lightgbm as lgb
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import log_loss

def objective(trial):
    params = dict(
        objective="binary",
        n_estimators=3000,
        learning_rate=trial.suggest_float("learning_rate", 1e-3, 0.2, log=True),
        num_leaves=trial.suggest_int("num_leaves", 15, 255, log=True),
        min_child_samples=trial.suggest_int("min_child_samples", 5, 200, log=True),
        subsample=trial.suggest_float("subsample", 0.5, 1.0),
        subsample_freq=trial.suggest_int("subsample_freq", 0, 10),
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
        reg_alpha=trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        reg_lambda=trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        min_split_gain=trial.suggest_float("min_split_gain", 1e-8, 1.0, log=True),
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    cv = TimeSeriesSplit(n_splits=5)
    scores = []
    for tr, va in cv.split(X):
        clf = lgb.LGBMClassifier(**params)
        clf.fit(
            X.iloc[tr], y.iloc[tr],
            eval_set=[(X.iloc[va], y.iloc[va])],
            callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
        )
        scores.append(log_loss(y.iloc[va], clf.predict_proba(X.iloc[va])[:, 1]))
    return float(np.mean(scores))

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=50, show_progress_bar=True)
print(study.best_params)
```

`optuna.integration.LightGBMPruningCallback` prunes unpromising trials mid-training.
For an automated stepwise tuner that walks the parameters in importance order, see
`optuna.integration.lightgbm.LightGBMTuner` (a drop-in for `lgb.train`).

See the upstream
[Parameters-Tuning guide](https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html)
for the "better accuracy" / "faster speed" / "deal with over-fitting" branches.
