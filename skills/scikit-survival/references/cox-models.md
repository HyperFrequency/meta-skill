# Cox Proportional Hazards Models

Cox models are **semi-parametric**: they relate covariates to the hazard without
specifying the baseline hazard shape. The hazard for subject *i* is

**h_i(t) = h_0(t) · exp(β·x_i)**

with `h_0(t)` an unspecified baseline hazard and `β` the log-hazard-ratio
coefficients. The core assumption is **proportional hazards** — the hazard ratio
between any two subjects is constant over time.

## CoxPHSurvivalAnalysis

Standard Cox model. Best when you have a modest number of features and want
interpretable hazard ratios.

Key parameters:

- `alpha` — ridge (L2) penalty strength; default `0` (unpenalized).
- `ties` — tied-time handling, `"breslow"` (default) or `"efron"` (usually
  more accurate with many ties).
- `n_iter` — max Newton-Raphson iterations.

```python
from sksurv.linear_model import CoxPHSurvivalAnalysis
from sksurv.datasets import load_gbsg2
from sksurv.preprocessing import encode_categorical

X, y = load_gbsg2()
X = encode_categorical(X)

model = CoxPHSurvivalAnalysis().fit(X, y)
coef  = model.coef_                       # log hazard ratios
risk  = model.predict(X)                  # relative risk score
surv  = model.predict_survival_function(X)     # per-subject S(t) step functions
chf   = model.predict_cumulative_hazard_function(X)
```

**Coefficient reading**: positive β raises the hazard (shorter survival);
`exp(β)` is the hazard ratio per one-unit increase (β=0.693 → HR≈2.0). Risk
scores are relative — use survival functions for absolute probabilities.

## CoxnetSurvivalAnalysis

Cox with an **elastic-net** penalty. Use for high-dimensional / `p > n` data,
automatic feature selection, or multicollinearity.

- `l1_ratio` — mix of L1/L2. `1.0` = Lasso (sparse, selects features); near `0`
  = Ridge (shrinks all). `0` exactly is not allowed; use a small value for
  ridge-like behavior.
- `alpha_min_ratio` — smallest penalty in the path, as a fraction of the
  largest. Use `"auto"`, or e.g. `0.01`; set small (`0.001`) when `n < p`.
- `n_alphas` — number of penalties along the regularization path.
- `fit_baseline_model` — set `True` if you need `predict_survival_function`.

```python
from sksurv.linear_model import CoxnetSurvivalAnalysis

model = CoxnetSurvivalAnalysis(l1_ratio=0.9, alpha_min_ratio=0.01,
                               fit_baseline_model=True).fit(X, y)
alphas = model.alphas_            # full regularization path
import numpy as np
selected = np.where(model.coef_[:, -1] != 0)[0]   # nonzero features at final alpha
```

Tune `alpha`/`l1_ratio` with cross-validation using a survival-aware scorer:

```python
from sklearn.model_selection import GridSearchCV
from sksurv.metrics import as_concordance_index_ipcw_scorer

grid = {"estimator__l1_ratio": [0.5, 0.9], "estimator__alpha_min_ratio": [0.01, 0.001]}
cv = GridSearchCV(as_concordance_index_ipcw_scorer(CoxnetSurvivalAnalysis()),
                  grid, cv=5).fit(X, y)
```

Note: `as_*_scorer(estimator)` wraps the estimator so its `.score` returns the
survival metric; prefix param-grid keys with `estimator__` accordingly.

## IPCRidge

Inverse-probability-of-censoring-weighted **ridge regression** for an
**accelerated failure time (AFT)** model. Unlike Cox, AFT models predict
**log survival time** directly — features multiply survival time rather than the
hazard. Consider it when the AFT framing fits better or censoring is heavy.

```python
from sksurv.linear_model import IPCRidge
model = IPCRidge(alpha=1.0).fit(X, y)
log_time = model.predict(X)     # predicted log survival time
```

## Model choice

| Use | When |
|-----|------|
| `CoxPHSurvivalAnalysis` | few features, want interpretable hazard ratios |
| `CoxnetSurvivalAnalysis` | `p >> n`, need feature selection or handle collinearity |
| `IPCRidge` | AFT framing preferred, model time directly, high censoring |

## Checking the proportional-hazards assumption

sksurv does not test PH directly. Verify with Schoenfeld residuals or log-log
survival plots (available in `lifelines`). If PH is violated, consider
stratifying on the offending covariate, time-varying coefficients (lifelines),
or a non-PH model (RSF, gradient boosting, AFT).
