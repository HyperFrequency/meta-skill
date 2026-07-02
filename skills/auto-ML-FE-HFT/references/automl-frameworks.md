# Section A — AutoML framework comparison + canonical usage

Sections labelled **Recommendation** are author's call; **Fact** cites a paper.

## A.1 The framework matrix

| Framework  | Sweet spot                          | Compute     | TS native?               | Interpretability       | Wall-clock      |
|------------|-------------------------------------|-------------|--------------------------|------------------------|-----------------|
| H2O AutoML | Large tabular, distributed          | CPU (cluster)| Limited                 | High (leaderboard+viz) | Minutes–hours   |
| AutoGluon  | Mixed types, tabular+text+image+TS  | CPU + GPU   | Yes (TimeSeriesPredictor)| Medium                 | Minutes–hours   |
| FLAML      | Fast iteration, small budget        | CPU         | Limited                  | High (single learner)  | Seconds–minutes |
| TPOT       | Exportable sklearn pipelines (GP)   | CPU         | No                       | Very high (.py export) | Hours           |
| PyCaret    | Prototyping, EDA, low-code          | CPU + some GPU| Yes (TSForecasting)    | High (compare_models)  | Minutes         |

**Recommendation:** fresh CPU-only quant project — FLAML for a 30-min baseline, then H2O AutoML or AutoGluon for the production candidate. TPOT only when you need an exportable readable sklearn pipeline. PyCaret for EDA + leaderboard before committing. With heavy categoricals (symbol/exchange/regime), bypass AutoML and go to **CatBoost** (`catboost` skill) — the others mis-encode high-cardinality categoricals.

## A.2 H2O AutoML — canonical usage

Large tabular CPU; leaderboard across GLM/GBM/XGBoost/DL/stacked ensembles; distributed CPU > GPU.

```python
# H2O AutoML — binary direction classification. Verified API via Context7.
import h2o
from h2o.automl import H2OAutoML

h2o.init()  # spins up a local JVM cluster

train = h2o.import_file("features_train.parquet")  # or .csv
test  = h2o.import_file("features_test.parquet")

y = "direction"                       # 1 = up, 0 = down
x = [c for c in train.columns if c != y]

# Binary classification — response must be a factor.
train[y] = train[y].asfactor()
test[y]  = test[y].asfactor()

aml = H2OAutoML(
    max_runtime_secs=1800,            # 30 minutes
    sort_metric="AUC",
    nfolds=5,                          # k-fold; for time series, see note below
    balance_classes=True,
    seed=42,
)
aml.train(x=x, y=y, training_frame=train)

print(aml.leaderboard.head(20))       # ranked candidate models
perf = aml.leader.model_performance(test)
print(perf.auc(), perf.logloss())
```

**Time-series caveat:** H2O AutoML k-folds by default — pre-split chronologically and pass `validation_frame` or accept the leakage. Cross-link `model-evaluation` for the walk-forward pattern.

## A.3 AutoGluon — canonical usage (tabular + time-series)

Mixed data types or one-shot **TimeSeriesPredictor**. `presets='best_quality'` ensembles ~14 base learners — heavy on disk/RAM.

```python
# AutoGluon Tabular — direction classification. Verified via Context7.
from autogluon.tabular import TabularPredictor
import pandas as pd

train_df = pd.read_parquet("features_train.parquet")
test_df  = pd.read_parquet("features_test.parquet")

predictor = TabularPredictor(
    label="direction",
    eval_metric="roc_auc",
    path="./ag_tabular_run",
).fit(
    train_df,
    time_limit=1800,             # 30 minutes
    presets="best_quality",      # 'medium_quality' for faster baseline
)

print(predictor.leaderboard(test_df))
print(predictor.evaluate(test_df))
```

```python
# AutoGluon TimeSeries — panel multi-step forecast. Verified via Context7.
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor

# Expect long-format dataframe: columns [item_id, timestamp, target, ...covariates].
ts_df = TimeSeriesDataFrame.from_data_frame(
    pd.read_parquet("panel.parquet"),
    id_column="symbol",
    timestamp_column="ts",
)

predictor = TimeSeriesPredictor(
    prediction_length=48,        # forecast horizon (e.g., 48 bars)
    target="close",
    eval_metric="MASE",
    quantile_levels=[0.1, 0.5, 0.9],   # probabilistic intervals
    path="./ag_ts_run",
).fit(
    ts_df,
    presets="medium_quality",    # 'best_quality' includes Chronos foundation models
    time_limit=1800,
)

forecasts = predictor.predict(ts_df)
print(predictor.leaderboard(ts_df))
```

## A.4 FLAML — canonical usage

CPU laptop, ≤5-min budget, baseline that beats default-hyperparameter XGBoost. CFO/BlendSearch converges fast on small budgets. *Inline API unverified — check `flaml --version`.*

```python
# FLAML AutoML — fast tabular baseline. NOT verified via Context7 — confirm against docs.
from flaml import AutoML
import pandas as pd

df = pd.read_parquet("features_train.parquet")
X = df.drop(columns=["direction"])
y = df["direction"]

automl = AutoML()
automl.fit(
    X_train=X, y_train=y,
    task="classification",
    metric="roc_auc",
    time_budget=300,              # 5 minutes
    estimator_list=["lgbm", "xgboost", "catboost", "rf", "extra_tree"],
    eval_method="cv",
    n_splits=5,
    seed=42,
)
print(automl.best_estimator, automl.best_config)
print("Best ROC AUC:", 1 - automl.best_loss)
```

## A.5 TPOT — canonical usage

Use when you need an **exportable sklearn pipeline as .py** — useful when ML governance demands you read every preprocessing step. Wall-clock expensive (GP).

```python
# TPOT — genetic programming over sklearn pipelines. Verified via Context7.
import tpot
import sklearn.datasets, sklearn.model_selection, sklearn.metrics

X, y = sklearn.datasets.load_breast_cancer(return_X_y=True)  # replace with your features
X_train, X_test, y_train, y_test = sklearn.model_selection.train_test_split(
    X, y, test_size=0.2, random_state=42
)

if __name__ == "__main__":      # TPOT requires guard when run from a script
    clf = tpot.TPOTClassifier(
        search_space="linear-light",
        scorers=["roc_auc_ovr"],
        scorers_weights=[1],
        cv=5,
        max_time_mins=30,
        max_eval_time_mins=5,
        n_jobs=4,
        early_stop=5,
        random_state=42,
        verbose=2,
    )
    clf.fit(X_train, y_train)
    auroc = sklearn.metrics.roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1])
    print(f"AUROC: {auroc:.4f}")
    print(clf.fitted_pipeline_)   # exportable sklearn Pipeline
```

## A.6 PyCaret — canonical usage

Rapid prototyping, low-code, leaderboard-driven. Good for the first 30 min of a project; weaker for production hand-off.

```python
# PyCaret time-series forecasting — leaderboard + tuned model. Verified via Context7.
from pycaret.time_series import TSForecastingExperiment
import pandas as pd

y = pd.read_parquet("univariate_target.parquet")["close"]  # DateTimeIndex required

exp = TSForecastingExperiment()
exp.setup(
    data=y,
    fh=24,                       # forecast horizon
    fold=5,
    session_id=42,
)
best = exp.compare_models(sort="MASE", turbo=False)
tuned = exp.tune_model(best)
preds = exp.predict_model(tuned, fh=24)
```

## A.7 Cross-skill integration with `xgboost` / `lightgbm` / `catboost`

Every AutoML framework above tends to fit a boosted tree as the leader on tabular HFT data (matches Borisov 2022 — see decision-tree reference). When the leaderboard picks XGBoost / LightGBM / CatBoost, hand off to the dedicated skill for walk-forward CV (`has_time=True` is CatBoost-only), categorical handling (CatBoost > LightGBM > XGBoost), GPU (`task_type="GPU"` for CatBoost, `tree_method="hist", device="cuda"` for XGBoost ≥2.0), and per-model SHAP.
