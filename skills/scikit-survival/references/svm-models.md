# Survival Support Vector Machines

Survival SVMs adapt margin-based learning to censored data by optimizing a
**ranking objective**: subjects with shorter survival should receive higher risk
scores. They output a risk score via `.predict()` but generally **not** survival
functions.

**Always standardize features before fitting an SVM** — the objective is
scale-sensitive.

## When to reach for an SVM

Good fit: medium datasets (~100–10,000 samples), need for non-linear boundaries
(kernel variants), margin-based regularization, a well-defined feature space.

Poor fit: very large data (ensembles are faster), need for interpretable
coefficients (use Cox), need for survival-function output (use RSF/Cox), or very
high dimensions (use penalized Cox / gradient boosting).

## FastSurvivalSVM (linear)

Linear survival SVM via optimized (coordinate-descent style) solver — fast,
scales well.

- `alpha` (default 1.0) — regularization; higher = more.
- `rank_ratio` (default 1.0) — trade-off between pure ranking (1.0) and a
  regression term (toward 0.0, enabling time prediction).
- `max_iter`, `tol` — optimizer controls.

```python
from sksurv.svm import FastSurvivalSVM
svm = FastSurvivalSVM(alpha=1.0, max_iter=100, tol=1e-5, random_state=42).fit(X, y)
risk = svm.predict(X_test)
```

## FastKernelSurvivalSVM (non-linear)

Kernelized version for non-linear relationships.

- `kernel` — `"linear"`, `"poly"`, `"rbf"` (default, most common), `"sigmoid"`,
  or a callable.
- `gamma` — kernel width for rbf/poly/sigmoid (`"scale"`, `"auto"`, or a float).
- `degree`, `coef0` — polynomial/sigmoid controls.
- `alpha`, `rank_ratio`, `max_iter` — as above.

```python
from sksurv.svm import FastKernelSurvivalSVM
svm = FastKernelSurvivalSVM(kernel="rbf", alpha=1.0, gamma="scale",
                            max_iter=50, random_state=42).fit(X, y)
```

Cost scales roughly O(n²·p), so kernel SVMs get slow on large `n`.

## Other variants

- `HingeLossSurvivalSVM` — hinge (rather than squared-hinge) loss; more
  classification-SVM-like, sparser solutions. Params include `alpha`,
  `fit_intercept`.
- `NaiveSurvivalSVM` — original QP formulation; correct but O(n³), for small data
  or benchmarking only.
- `MinlipSurvivalAnalysis` — minimum-Lipschitz objective; an alternative
  formulation for research use.

## Tuning

```python
from sklearn.model_selection import GridSearchCV
from sksurv.metrics import as_concordance_index_ipcw_scorer

# Linear: tune alpha
cv = GridSearchCV(as_concordance_index_ipcw_scorer(FastSurvivalSVM()),
                  {"estimator__alpha": [0.1, 0.5, 1.0, 5.0, 10.0, 50.0]},
                  cv=5, n_jobs=-1).fit(X, y)

# RBF: tune alpha and gamma
cv = GridSearchCV(as_concordance_index_ipcw_scorer(FastKernelSurvivalSVM(kernel="rbf")),
                  {"estimator__alpha": [0.1, 1.0, 10.0],
                   "estimator__gamma": ["scale", 0.01, 0.1, 1.0]},
                  cv=5, n_jobs=-1).fit(X, y)
```

Put scaling and the SVM in a `Pipeline` so the scaler is refit per CV fold.

## ClinicalKernelTransform

A kernel that mixes heterogeneous clinical variables (age, stage, grade) with
high-dimensional molecular data, weighting the two appropriately. Use when you
integrate clinical + genomic features.

```python
from sksurv.kernels import ClinicalKernelTransform
from sksurv.svm import FastKernelSurvivalSVM
from sklearn.pipeline import make_pipeline

model = make_pipeline(ClinicalKernelTransform(), FastKernelSurvivalSVM())
# ClinicalKernelTransform can be fit on the clinical feature matrix to build
# the kernel; consult the API for the exact clinical/molecular split it expects.
```

## Complexity and selection

| Model | Non-linear | Scalability | Notes |
|-------|-----------|-------------|-------|
| FastSurvivalSVM | No | High (O(n·p)/iter) | strong linear baseline |
| FastKernelSurvivalSVM | Yes | Medium (O(n²·p)) | rbf for non-linearity |
| HingeLossSurvivalSVM | No | High | sparse |
| NaiveSurvivalSVM | No | Low (O(n³)) | small data only |

Start with `FastSurvivalSVM`; add `FastKernelSurvivalSVM(kernel="rbf")` if
non-linearity is expected; always scale; compare against RSF and gradient
boosting.
