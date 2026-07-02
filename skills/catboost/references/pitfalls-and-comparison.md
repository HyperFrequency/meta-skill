# CatBoost — Pitfalls, Cross-Comparison, and Further Reading

## Common pitfalls

1. **Forgetting `has_time=True` on time-series data** — by default CatBoost generates random
   permutations to compute ordered target statistics for categoricals. On chronological data this
   can leak future targets into past encodings. Always set `has_time=True` for financial /
   sequential data; this fixes the permutation to the row order.

2. **`cat_features` must be specified at `Pool`/`fit` time, not later** — CatBoost computes
   statistics over the categorical columns during model construction. Passing them only at
   `predict` time errors out. Either build a `Pool` with `cat_features=`, or pass to
   `fit(..., cat_features=cat_cols)`.

3. **GPU depth limit is 8** — `depth > 8` with `task_type="GPU"` either errors or silently caps.
   If you need deeper trees, fall back to `task_type="CPU"` (max depth 16).

4. **`MultiRMSE` requires specific defaults** — the upstream tutorial uses
   `bootstrap_type="Bayesian"`, `boost_from_average=False`, `leaf_estimation_iterations=1`,
   `leaf_estimation_method="Gradient"`. Deviating (e.g., Bernoulli bootstrap) can fail or
   converge poorly.

5. **CatBoost is slower than LightGBM/XGBoost on small CPU jobs** — but its inference is fast
   (oblivious trees). If train time dominates and you have no categoricals, LightGBM/XGBoost are
   better choices. If inference latency dominates, CatBoost often wins.

6. **String categoricals are first-class — don't pre-encode** — passing one-hot or label-encoded
   categoricals to CatBoost *and* listing them in `cat_features` confuses it. Either pass raw
   strings/ints and list them in `cat_features`, or pre-encode and **omit** them from
   `cat_features`. The former usually performs better thanks to ordered target encoding.

## Cross-comparison: CatBoost vs. XGBoost vs. LightGBM

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
- `xgboost` — see [`xgboost` skill](../../xgboost/SKILL.md) — broader ecosystem; needed when CatBoost's narrower bindings hurt
- `lightgbm` — see [`lightgbm` skill](../../lightgbm/SKILL.md) — typically faster training on dense numeric features
- [scikit-learn `HistGradientBoostingClassifier`](https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting) — pure-sklearn baseline; no native categorical handling
- [`treelite`](https://github.com/dmlc/treelite) — compile any of XGB/LGBM/CatBoost trees to a single inference DLL

### Academic papers
- Prokhorenkova, L., Gusev, G., Vorobev, A., Dorogush, A. V., Gulin, A. (2018). "CatBoost: unbiased boosting with categorical features." *NeurIPS 2018*. [arXiv:1706.09516](https://arxiv.org/abs/1706.09516) — the original paper; introduces *ordered boosting* (the permutation-driven fix to target leakage) and the symmetric/oblivious tree predictor
- Dorogush, A. V., Ershov, V., Gulin, A. (2018). "CatBoost: gradient boosting with categorical features support." [arXiv:1810.11363](https://arxiv.org/abs/1810.11363) — companion workshop paper, focuses on categorical encodings

### Tutorials & write-ups
- [Yandex official CatBoost intro](https://catboost.ai/en/docs/concepts/about) — author-team positioning of the algorithm
- [Symmetric/oblivious trees explainer](https://catboost.ai/en/docs/concepts/algorithm-main-stages_choosing-tree-structure) — why CatBoost is the fastest at inference time among the three

### Last cross-checked
2026-05-20 — via Context7 `/catboost/catboost` (19,893 snippets — heaviest coverage of the three
boosters) + upstream docs at `catboost.ai/en/docs/`; Auggie not indexed.
