---
name: vertex-ai-forecasting
description: Google Cloud Vertex AI managed time series forecasting via the `google-cloud-aiplatform` Python SDK. Covers the four supported training methods (AutoML, Temporal Fusion Transformer, TiDE / Time-Series Dense Encoder, Seq2Seq+), `TimeSeriesDataset`, training-job submission, batch prediction, and evaluation. Trigger on phrases like "Vertex AI forecast", "AutoML forecasting", "GCP forecasting pipeline", "TimeSeriesDataset", "managed forecasting on Google Cloud", "TiDE forecast", "AutoMLForecastingTrainingJob", "deploy a forecast model to Vertex". Use when the user wants a *managed* solution (no infra, batch predictions to GCS / BigQuery) instead of locally trained models.
license: Apache-2.0
metadata:
    skill-author: HyperFrequency
---

# Vertex AI Forecasting (Managed)

## When to use this skill

- You want a **managed** training pipeline that handles feature engineering, holiday lookups, hyperparameter search, and model serving - no GPUs to provision.
- You have **multi-series data in BigQuery or GCS** (CSV) and want to forecast many series at once (e.g. one model per SKU / ticker / region).
- You need **batch predictions to GCS or BigQuery** on a schedule.
- You want to A/B compare the four built-in architectures (AutoML / TFT / TiDE / Seq2Seq+) without writing any model code.

For a local TFT see `transformer-forecast`. For local ARIMA / Prophet / LSTM see the sibling skills. Use Vertex when "managed + reproducible cloud artefacts" matter more than "fastest local iteration".

## Install / setup

```bash
uv add google-cloud-aiplatform pandas numpy
```

Auth (one of):

```bash
# Interactive ADC (works for local dev)
gcloud auth application-default login

# Service-account key (for CI / containers)
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

You must also have:
- A GCP project with the **Vertex AI API enabled** (`gcloud services enable aiplatform.googleapis.com`).
- A **regional bucket** for staging (e.g. `gs://my-vertex-staging-us-central1`).
- Data in **BigQuery** (`bq://project.dataset.table`) or **GCS CSV** (`gs://bucket/file.csv`). Source must follow Vertex's forecasting schema: one column for `time`, one for `time_series_identifier`, one for `target`, plus covariates.

## Minimal working example

```python
from google.cloud import aiplatform

PROJECT  = "my-gcp-project"
REGION   = "us-central1"
BUCKET   = "gs://my-vertex-staging-us-central1"

aiplatform.init(project=PROJECT, location=REGION, staging_bucket=BUCKET)

# 1. Create (or load) a TimeSeriesDataset from BigQuery or GCS
ds = aiplatform.TimeSeriesDataset.create(
    display_name="prices-daily-2024",
    bq_source="bq://my-gcp-project.market.prices_daily",  # or gcs_source=["gs://.../prices.csv"]
)

# 2. Choose ONE of the four training-job classes
#    AutoMLForecastingTrainingJob                         - default AutoML ensemble
#    TemporalFusionTransformerForecastingTrainingJob       - TFT (interpretable attention)
#    TimeSeriesDenseEncoderForecastingTrainingJob         - TiDE (MLP-based, fast)
#    Seq2SeqPlusForecastingTrainingJob                    - encoder-decoder seq2seq+
job = aiplatform.TimeSeriesDenseEncoderForecastingTrainingJob(
    display_name="prices-tide-2024",
    optimization_objective="minimize-rmse",   # also: minimize-mae, minimize-mape, minimize-rmsle, ...
)

# 3. Run training (synchronous - blocks until done; use sync=False for fire-and-forget)
model = job.run(
    dataset=ds,
    target_column="close",
    time_column="date",
    time_series_identifier_column="symbol",
    available_at_forecast_columns=["day_of_week", "is_holiday"],   # known into future
    unavailable_at_forecast_columns=["volume"],                    # only known historically
    time_series_attribute_columns=["sector"],                      # static per series
    forecast_horizon=7,                                            # predict 7 days out
    context_window=28,                                             # use last 28 days as history
    data_granularity_unit="day",
    data_granularity_count=1,
    training_fraction_split=0.8,
    validation_fraction_split=0.1,
    test_fraction_split=0.1,
    budget_milli_node_hours=1000,                                  # 1000 = 1 node-hour
    model_display_name="prices-tide-v1",
    quantiles=[0.1, 0.5, 0.9],
    enable_probabilistic_inference=True,
)
print("model:", model.resource_name)

# 4. Batch predict -> GCS (forecasting does NOT support online endpoints as of 2024-2025)
job = model.batch_predict(
    job_display_name="prices-tide-batch-2025-q1",
    gcs_source=["gs://my-input/forecast_inputs.csv"],
    gcs_destination_prefix="gs://my-output/predictions/",
    instances_format="csv",
    predictions_format="csv",
    sync=True,
)
print("batch job:", job.resource_name, "state:", job.state)
```

## Key API surface

| Class / method | Purpose |
|---|---|
| `aiplatform.init(project, location, staging_bucket)` | Set defaults for all subsequent calls |
| `aiplatform.TimeSeriesDataset.create(display_name, bq_source=..., gcs_source=...)` | Register a managed time-series dataset (BigQuery or CSV) |
| `aiplatform.AutoMLForecastingTrainingJob(display_name, optimization_objective)` | Original AutoML ensemble (default fallback) |
| `aiplatform.TemporalFusionTransformerForecastingTrainingJob(...)` | TFT - quantile + interpretable attention |
| `aiplatform.TimeSeriesDenseEncoderForecastingTrainingJob(...)` | TiDE - dense-encoder MLP (fast, good baseline) |
| `aiplatform.Seq2SeqPlusForecastingTrainingJob(...)` | Encoder-decoder seq2seq+ |
| `job.run(dataset, target_column, time_column, time_series_identifier_column, forecast_horizon, context_window, data_granularity_unit, budget_milli_node_hours, ...)` | Submit training |
| `model.batch_predict(job_display_name, gcs_source=, gcs_destination_prefix=, bigquery_source=, bigquery_destination_prefix=)` | Batch inference (the only inference path for forecasting models) |
| `aiplatform.Model(model_name)` | Re-attach to an existing model by resource name |
| `model.list_model_evaluations()` / `model.get_model_evaluation()` | Pull MAE / RMSE / MAPE / quantile loss from the training-time test split |

### Column-role parameters

| Argument | Meaning |
|---|---|
| `target_column` | The value being forecasted |
| `time_column` | Timestamp column (ISO 8601 string or TIMESTAMP) |
| `time_series_identifier_column` | Identifies an individual series (e.g. ticker, store_id) |
| `available_at_forecast_columns` | Covariates known into the future (day-of-week, holiday flags, scheduled promos) |
| `unavailable_at_forecast_columns` | Historical-only covariates (lagged volume, exogenous regressors only available after the fact) |
| `time_series_attribute_columns` | Static per series (sector, category) |
| `forecast_horizon` | Number of granularity steps to forecast |
| `context_window` | Number of historical steps the model sees |
| `data_granularity_unit` | `"minute"` / `"hour"` / `"day"` / `"week"` / `"month"` / `"year"` |
| `data_granularity_count` | Multiplier (e.g. `5`-`minute` = 5-min bars) |
| `quantiles` | List in `(0, 1)` - requires `enable_probabilistic_inference=True` |

## Evaluation

Vertex emits its own test-split metrics as a `ModelEvaluation` artifact:

```python
ev = model.get_model_evaluation()
print(ev.metrics)
# typical keys: meanAbsoluteError, meanAbsolutePercentageError,
#               rootMeanSquaredError, rootMeanSquaredLogError,
#               rSquared, weightedAbsolutePercentageError,
#               quantileMetrics (when probabilistic inference is enabled)
```

For a hand-rolled holdout on truly *future* data, run `batch_predict` against a CSV/BQ table whose targets you have privately, then in your own code:

```python
import pandas as pd, numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

preds = pd.read_csv("gs://my-output/predictions/prediction-...csv")
truth = pd.read_csv("local_actuals.csv")
merged = preds.merge(truth, on=["symbol", "date"], suffixes=("_hat", ""))

mae  = mean_absolute_error(merged["close"], merged["predicted_close.value"])
rmse = np.sqrt(mean_squared_error(merged["close"], merged["predicted_close.value"]))
print(f"MAE {mae:.4f}  RMSE {rmse:.4f}")
```

The exact prediction-column path (`predicted_<target>.value`, `predicted_<target>.quantile_predictions`) depends on whether you enabled probabilistic inference. Inspect one output row first.

## Common pitfalls

1. **Forecasting models do not support online endpoints.** As of the 2024-2025 docs, `model.deploy()` for forecasting raises - inference is **batch only** via `batch_predict`. Plan for an asynchronous workflow. // unverified for future SDK versions - see https://docs.cloud.google.com/vertex-ai/docs/tabular-data/forecasting/get-predictions
2. **`budget_milli_node_hours` is in *milli* node-hours.** `1000` = 1 node-hour, `10_000` = 10 node-hours. The minimum is around 1000 for AutoML; check the per-method docs.
3. **Wrong column role.** Putting a column that *is* known into the future into `unavailable_at_forecast_columns` (or vice versa) silently degrades accuracy without an error. Audit each column.
4. **`forecast_horizon + context_window` must fit your data.** Each series needs at least `context_window + forecast_horizon` historical rows in the training split, else Vertex drops it.
5. **Granularity mismatch.** If `data_granularity_unit="day"` but your `time_column` has multiple rows per day per series, training fails. Aggregate to one row per `(series, time)` first.
6. **Region / quota.** `aiplatform.init(location=...)` must use a region that supports your method (TFT, TiDE, Seq2Seq+ are in fewer regions than AutoML). Start with `us-central1` and check quota for "Forecasting training compute".
7. **Costs are non-trivial.** A budget of `8000` milli-node-hours on `n1-standard-8` accumulates real charges. Always start with `budget_milli_node_hours=1000` for smoke tests.
8. **Auth fails silently in notebooks.** If `aiplatform.init()` succeeds but `TimeSeriesDataset.create()` 403s, your ADC is for a different project. Re-run `gcloud auth application-default login` and verify with `gcloud config get-value project`.

## References

### Primary library / service
- [googleapis/python-aiplatform](https://github.com/googleapis/python-aiplatform) — Vertex AI Python SDK (issues, releases, source for `google.cloud.aiplatform`)
- [Vertex AI Python SDK reference](https://cloud.google.com/python/docs/reference/aiplatform/latest) — cross-checked against the current GA channel
- [SDK samples directory](https://github.com/googleapis/python-aiplatform/tree/main/samples) — runnable end-to-end examples
- [SDK release notes](https://cloud.google.com/vertex-ai/docs/release-notes) — service-level changes (forecasting methods are added / GA-promoted here)

### Deep-dive docs (specific pages worth bookmarking)
- [Forecasting overview](https://cloud.google.com/vertex-ai/docs/tabular-data/forecasting/overview) — when to use forecasting vs regression vs Gemini-based approaches
- [Forecasting methods (AutoML, Seq2Seq+, TFT, TiDE)](https://cloud.google.com/vertex-ai/docs/tabular-data/forecasting/train-model) — picks the right `*ForecastingTrainingJob` class; lists per-method region availability
- [Prepare training data](https://cloud.google.com/vertex-ai/docs/tabular-data/forecasting/prepare-data) — the schema contract (time/series/target columns, granularity, gaps); read this *before* uploading
- [Get batch predictions](https://cloud.google.com/vertex-ai/docs/tabular-data/forecasting/get-predictions) — BigQuery + GCS sinks, the only supported delivery modes for forecast batches
- [Quantile + probabilistic outputs](https://cloud.google.com/vertex-ai/docs/tabular-data/forecasting/get-quantile-predictions) — how to ask for `[0.1, 0.5, 0.9]` quantiles per series
- [Forecasting hierarchical groups](https://cloud.google.com/vertex-ai/docs/tabular-data/forecasting/hierarchical-forecasts) — required when you have product/region hierarchies
- [Holiday regions](https://cloud.google.com/vertex-ai/docs/tabular-data/forecasting/data-preparation#holiday) — pre-supplied calendar features that beat hand-rolled dummies
- [Vertex AI Forecasting pricing](https://cloud.google.com/vertex-ai/pricing#forecasting) — milli-node-hours and forecast-row pricing; the smoke-test budget is critical
- [Quotas & limits](https://cloud.google.com/vertex-ai/docs/quotas) — training compute quotas + per-region method availability

### Adjacent / alternative libraries
- [BigQuery ML `ARIMA_PLUS` / `ARIMA_PLUS_XREG`](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-time-series) — SQL-native forecasting inside BigQuery, no Vertex job needed; fits when your data already lives in BQ
- [AWS Forecast (deprecated for new customers, see SageMaker Canvas)](https://aws.amazon.com/forecast/) — the closest non-GCP equivalent
- [Azure AutoML Forecasting](https://learn.microsoft.com/en-us/azure/machine-learning/concept-automl-forecasting-methods) — Microsoft's equivalent managed forecaster
- For self-hosted / on-prem: `transformer-forecast` skill (HF TST + TFT in pytorch-forecasting) gives you the same model families without the per-row billing

### Tutorials & write-ups
- [Vertex AI Forecasting codelab](https://codelabs.developers.google.com/codelabs/vertex-ai-forecasting) — official end-to-end walkthrough with the synthetic retail sample
- [Forecasting with Vertex AI on YouTube (Google Cloud Tech)](https://www.youtube.com/results?search_query=vertex+ai+forecasting) — official video coverage by the product team
- [`gcloud auth application-default` setup](https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login) — required when the SDK 403s in notebooks

### Last cross-checked
2026-05-20 — via Context7 `/googleapis/python-aiplatform` + `/websites/cloud_google_vertex-ai`; Auggie not indexed for `python-aiplatform`.
