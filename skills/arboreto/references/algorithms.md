# Algorithm Selection and Tuning

Arboreto's two front-end algorithms and the low-level `diy()` escape hatch for
custom regressors.

## Shared Inference Strategy

Both algorithms implement the same multiple-regression recipe:

1. For every target gene, train a tree-ensemble regressor that predicts its
   expression from the expression of the candidate regulators (TFs).
2. Extract the regressor's feature importances — one per regulator.
3. Emit each regulator as a `TF → target` edge weighted by that importance.

They differ only in the regressor and its speed/robustness trade-off. Output
format is identical, so the two are drop-in interchangeable.

## GRNBoost2 (default)

```python
from arboreto.algo import grnboost2

network = grnboost2(
    expression_data=expression_matrix,
    gene_names=None,             # required only for NumPy input
    tf_names='all',              # or a list / load_tf_names(...)
    client_or_address='local',   # or a Dask Client / scheduler address
    seed=None,                   # set for reproducibility
    verbose=False,
)
```

- **Method:** stochastic gradient boosting (scikit-learn `GradientBoostingRegressor`)
  with early-stopping regularization.
- **Why default:** substantially faster than GENIE3 and built for large
  datasets (tens of thousands of observations, e.g. single-cell RNA-seq).

## GENIE3

```python
from arboreto.algo import genie3

network = genie3(
    expression_data=expression_matrix,
    tf_names=tf_names,
    seed=42,
)
```

- **Method:** random forest (scikit-learn `RandomForestRegressor`).
- **Role:** the original, well-established GRN method. Use it to reproduce
  published GENIE3 results, to validate GRNBoost2 edges, or on small/medium
  datasets where its extra cost is affordable.

## Custom Regressors via `diy()`

`grnboost2` and `genie3` are thin wrappers over the general
`arboreto.algo.diy(...)`, which exposes the regressor and its kwargs directly.
Use it when you need to tune the ensemble (tree count, depth, features) rather
than pass regressor kwargs into `grnboost2`, which does not accept them.

```python
from arboreto.algo import diy

network = diy(
    expression_data=expression_matrix,
    regressor_type='GBM',        # 'GBM' = GRNBoost2, 'RF' = GENIE3, 'ET' = ExtraTrees variant
    regressor_kwargs={           # scikit-learn kwargs for the chosen regressor
        'n_estimators': 500,
        'max_features': 'sqrt',
        'learning_rate': 0.01,
    },
    tf_names=tf_names,
    seed=42,
)
```

`regressor_type` options:

| Value | Regressor | Equivalent front-end |
|-------|-----------|----------------------|
| `'GBM'` | `GradientBoostingRegressor` | `grnboost2` |
| `'RF'` | `RandomForestRegressor` | `genie3` |
| `'ET'` | `ExtraTreesRegressor` | GENIE3-style alternative |

Arboreto ships sensible default kwargs for each regressor in `arboreto.core`
(`GBM_KWARGS`, `SGBM_KWARGS`, `RF_KWARGS`, `ET_KWARGS`); the front-end functions
apply these automatically. When calling `diy()` you supply `regressor_kwargs`
yourself — start from those defaults and adjust.

## Early Stopping (GRNBoost2)

GRNBoost2 halts boosting when the boosting training loss stops improving over a
sliding window, controlled by `early_stop_window_length` (default `25`). A larger window
lets boosting run longer (more estimators, higher cost); a smaller window stops
sooner. It is exposed through `diy()`.

## Choosing and Configuring

1. **Default to `grnboost2`** — faster, scales to large data, comparable edges.
2. **Use `genie3`** only for GENIE3-reproduction, validation, or small data.
3. **Drop to `diy()`** when you need explicit control of `n_estimators`,
   `max_features`, `max_depth`, `learning_rate`, or the early-stop window.
4. **Always set `seed=`** — both regressors subsample stochastically.
