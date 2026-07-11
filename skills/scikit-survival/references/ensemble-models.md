# Ensemble and Tree Models

Tree-based survival models capture non-linearities and interactions without
assuming proportional hazards. All expose `.predict()` (risk score),
`.predict_survival_function()`, and `.predict_cumulative_hazard_function()`.

## RandomSurvivalForest

Bagged survival trees. Each tree is grown on a bootstrap sample; at each node a
random feature subset is considered; terminal nodes hold Kaplan-Meier /
Nelson-Aalen estimates that are averaged across the forest. Robust, low-tuning,
good when `n > ~100`.

Key parameters:

- `n_estimators` — number of trees (default 100); more = more stable, slower.
- `max_depth` — tree depth cap (default unlimited).
- `min_samples_split` (default 6) / `min_samples_leaf` (default 3) — larger
  values regularize.
- `max_features` — `"sqrt"` (good default), `"log2"`, or `None`.
- `n_jobs=-1` — parallelize over cores; set `random_state` for reproducibility.

```python
from sksurv.ensemble import RandomSurvivalForest

rsf = RandomSurvivalForest(
    n_estimators=1000, min_samples_split=10, min_samples_leaf=15,
    max_features="sqrt", n_jobs=-1, random_state=42,
).fit(X, y)
risk = rsf.predict(X)
surv = rsf.predict_survival_function(X)
```

### Feature importance — use permutation, not impurity

Impurity-based importance is unreliable for survival trees. Use
`permutation_importance` with a survival scorer:

```python
from sklearn.inspection import permutation_importance
from sksurv.metrics import concordance_index_censored

def c_index_scorer(model, X, y):
    return concordance_index_censored(y["event"], y["time"], model.predict(X))[0]

imp = permutation_importance(rsf, X, y, n_repeats=10, random_state=42,
                             scoring=c_index_scorer)
importance = imp.importances_mean
```

## GradientBoostingSurvivalAnalysis

Sequentially adds regression trees, each correcting the current ensemble.
Highest performance with careful tuning; captures complex non-linear structure.

Loss functions (`loss`):

- `"coxph"` (default) — Cox partial likelihood; keeps a PH interpretation.
- `"ipcwls"` — IPCW least squares, an AFT-style loss modeling time directly.

Regularization levers:

- `learning_rate` (default 0.1) — shrinks each tree's contribution; smaller
  needs more `n_estimators` but generalizes better (typical 0.01–0.1).
- `subsample` (<1.0) — stochastic gradient boosting; typical 0.5–0.9.
- `dropout_rate` (>0) — randomly drops earlier trees for robustness.
- `max_depth` (default 3), `min_samples_leaf`, `max_features`.

```python
from sksurv.ensemble import GradientBoostingSurvivalAnalysis

gbs = GradientBoostingSurvivalAnalysis(
    loss="coxph", learning_rate=0.05, n_estimators=200,
    subsample=0.8, dropout_rate=0.1, max_depth=3, random_state=42,
).fit(X_train, y_train)
```

### Early stopping

Hold out a validation fraction and stop when it stops improving:

```python
gbs = GradientBoostingSurvivalAnalysis(
    n_estimators=1000, learning_rate=0.01, max_depth=3,
    validation_fraction=0.2, n_iter_no_change=10, random_state=42,
).fit(X_train, y_train)
print("iterations used:", gbs.n_estimators_)
```

### Tuning

```python
from sklearn.model_selection import GridSearchCV
from sksurv.metrics import as_concordance_index_ipcw_scorer

# as_*_scorer wraps the estimator, so grid keys take an "estimator__" prefix
grid = {"estimator__learning_rate": [0.01, 0.05, 0.1],
        "estimator__n_estimators": [100, 200, 300],
        "estimator__max_depth": [3, 5], "estimator__subsample": [0.8, 1.0]}
cv = GridSearchCV(as_concordance_index_ipcw_scorer(GradientBoostingSurvivalAnalysis()),
                  grid, cv=5, n_jobs=-1).fit(X, y)
```

## ComponentwiseGradientBoostingSurvivalAnalysis

Boosting with **component-wise least squares** base learners → a sparse
**linear** model with automatic feature selection (Lasso-like). Use when you
want interpretable coefficients plus selection in high dimensions.

```python
from sksurv.ensemble import ComponentwiseGradientBoostingSurvivalAnalysis

cgb = ComponentwiseGradientBoostingSurvivalAnalysis(
    loss="coxph", learning_rate=0.1, n_estimators=100).fit(X, y)
selected = [i for i, c in enumerate(cgb.coef_) if c != 0]
```

## ExtraSurvivalTrees

Like RSF but split thresholds are chosen at random, not optimized. More
regularization and faster training; useful with limited data.

```python
from sksurv.ensemble import ExtraSurvivalTrees
est = ExtraSurvivalTrees(n_estimators=100, random_state=42).fit(X, y)
```

## Quick comparison

| Model | Interpretability | Performance | Speed |
|-------|------------------|-------------|-------|
| RandomSurvivalForest | Low | High | Medium |
| GradientBoostingSurvivalAnalysis | Low | Highest (tuned) | Slow |
| ComponentwiseGradientBoosting | High (linear, sparse) | Medium | Fast |
| ExtraSurvivalTrees | Low | Medium–High | Fast |

Defaults: best raw performance → tuned gradient boosting; best balance → RSF;
best interpretability → componentwise boosting; fastest → extra trees.
