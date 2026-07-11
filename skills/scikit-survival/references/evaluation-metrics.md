# Evaluation Metrics for Survival Models

Standard ML metrics (accuracy, R²) are invalid under censoring. Use the
censoring-aware metrics in `sksurv.metrics`, which fall into three families:
concordance index, time-dependent AUC, and Brier score.

## Concordance index (discrimination / ranking)

Probability that, for a random comparable pair, the model orders their risk
correctly. Range 0.5 (random) to 1.0 (perfect); 0.7–0.8 is typically good.

### Harrell's — `concordance_index_censored`

Traditional estimator. Fine at **low censoring (<40%)** and for quick
development checks, but increasingly **optimistically biased** as censoring rises.

```python
from sksurv.metrics import concordance_index_censored
c_harrell = concordance_index_censored(y_test["event"], y_test["time"], risk_scores)[0]
```

### Uno's — `concordance_index_ipcw`

Inverse-probability-of-censoring-weighted; corrects the bias. Preferred when
**censoring > 40%**, for cross-study comparison, and for reporting. It **needs
`y_train`** to estimate the censoring distribution.

```python
from sksurv.metrics import concordance_index_ipcw
c_uno = concordance_index_ipcw(y_train, y_test, risk_scores)[0]
```

Both return a tuple `(cindex, concordant, discordant, tied_risk, tied_time)`;
take `[0]`.

## Time-dependent AUC — `cumulative_dynamic_auc`

Discrimination at specific horizons: how well the model separates subjects who
have an event by time *t* from those who do not. Needs `y_train`, `y_test`, risk
scores, and a set of times (inside the follow-up range).

```python
from sksurv.metrics import cumulative_dynamic_auc
times = [365, 730, 1095]                     # e.g. 1, 2, 3 years
auc, mean_auc = cumulative_dynamic_auc(y_train, y_test, risk_scores, times)
```

`auc` is per-time; `mean_auc` is a summary. Rising/falling `auc` shows how
discrimination changes with horizon.

## Brier score (discrimination + calibration)

Squared error between predicted survival probability and observed status,
extended to censoring. Range 0–1, **lower is better**; consumes **survival
functions**, not risk scores.

```python
from sksurv.metrics import brier_score, integrated_brier_score
import numpy as np

surv_funcs = model.predict_survival_function(X_test)

t = 1825
surv_at_t = np.asarray([fn(t) for fn in surv_funcs])   # S(t) per subject
bs = brier_score(y_train, y_test, surv_at_t, t)[1][0]

times = [365, 730, 1095, 1460, 1825]
surv_matrix = np.asarray([[fn(tt) for tt in times] for fn in surv_funcs])
ibs = integrated_brier_score(y_train, y_test, surv_matrix, times)
```

Choose `times` strictly inside the observed follow-up window, otherwise these
functions raise. Always compare against a Kaplan-Meier baseline to show the
model adds value.

## Using metrics in cross-validation / grid search

`as_concordance_index_ipcw_scorer(estimator, tau=...)` and
`as_integrated_brier_score_scorer(estimator, times=...)` **wrap the estimator**
(they are not `scoring=` objects) so its `.score` returns the survival metric.
Pass the wrapped estimator as the first `GridSearchCV`/`cross_val_score`
argument and prefix param-grid keys with `estimator__`:

```python
from sklearn.model_selection import cross_val_score, GridSearchCV
from sksurv.ensemble import RandomSurvivalForest
from sksurv.metrics import as_concordance_index_ipcw_scorer

scores = cross_val_score(as_concordance_index_ipcw_scorer(RandomSurvivalForest(random_state=42)),
                         X, y, cv=5)
print(f"CV C-index: {scores.mean():.3f} ± {scores.std():.3f}")

cv = GridSearchCV(
    as_concordance_index_ipcw_scorer(RandomSurvivalForest(random_state=42)),
    {"estimator__n_estimators": [100, 300], "estimator__min_samples_split": [10, 20]},
    cv=5, n_jobs=-1,
).fit(X, y)
```

Note the `estimator__` prefix on nested params, since the estimator is wrapped.

## Recommended reporting bundle

Report at least three complementary numbers:

```python
from sksurv.metrics import (concordance_index_censored, concordance_index_ipcw,
                            cumulative_dynamic_auc, integrated_brier_score)
import numpy as np

def evaluate(model, X_train, X_test, y_train, y_test):
    risk = model.predict(X_test)
    surv = model.predict_survival_function(X_test)
    times = np.percentile(y_test["time"][y_test["event"]], [25, 50, 75])
    surv_matrix = np.asarray([[fn(t) for t in times] for fn in surv])
    return {
        "c_harrell": concordance_index_censored(y_test["event"], y_test["time"], risk)[0],
        "c_uno":     concordance_index_ipcw(y_train, y_test, risk)[0],
        "mean_auc":  cumulative_dynamic_auc(y_train, y_test, risk, times)[1],
        "ibs":       integrated_brier_score(y_train, y_test, surv_matrix, times),
    }
```

## Which metric

- **Ranking is the goal, no calibrated probabilities needed** → Uno's C-index
  (the most common default).
- **Decisions at specific horizons** → time-dependent AUC.
- **Need calibrated probabilities / calibration matters** → (integrated) Brier
  score.

Best practice: report Uno's C-index + integrated Brier score + time-dependent
AUC at clinically meaningful times.
