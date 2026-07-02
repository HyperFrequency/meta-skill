# LightGBM vs. XGBoost vs. CatBoost

| Dimension | LightGBM | XGBoost | CatBoost |
|---|---|---|---|
| **Tree growth** | Leaf-wise (best-first) — fewer trees per unit accuracy | Level-wise depth-first | Symmetric / oblivious trees — very fast inference |
| **Speed (CPU)** | Fastest | Fast | Slowest of the three |
| **Categorical handling** | Native via `categorical_feature=` (int-encoded) | Native via `enable_categorical=True` (pandas category dtype) | Best-in-class — native strings, learned target/CTR encodings |
| **Missing values** | Per-split direction (`use_missing=true`) | Per-split direction | Treated as a distinct category/value |
| **GPU build** | OpenCL (`gpu`) or CUDA (`cuda`, source build) | CUDA wheel out of the box | CUDA wheel out of the box |
| **Distributed training** | Most mature (MPI, Dask, Ray) | Mature (Dask, Spark) | Less mature |
| **Time-series specific** | None built-in | None built-in | `has_time=True`, `TimeSeries` CV fold type |
| **Default win condition** | Many features + speed-critical | Broad baseline + ecosystem | Heavy categorical / time-ordered data |

## When to reach for a sibling instead

- Prefer **XGBoost** (`../xgboost/SKILL.md`) when ecosystem breadth (SHAP/ONNX/MLflow)
  matters most and you want the most universal GPU build.
- Prefer **CatBoost** (`../catboost/SKILL.md`) when categoricals dominate or when you
  need time-series-aware ordering (`has_time`).
- For explaining a trained LightGBM model, use the `shap` skill (`TreeExplainer`
  supports LightGBM boosters directly).
