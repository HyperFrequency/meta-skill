---
name: transformer-forecast
version: 0.1.0
description: Transformer-based time series forecasting. Covers two complementary stacks - HuggingFace `transformers.TimeSeriesTransformerForPrediction` (probabilistic encoder-decoder) and `pytorch-forecasting.TemporalFusionTransformer` (quantile TFT with variable selection + interpretable attention on top of PyTorch Lightning). Trigger on phrases like "fit a transformer to this series", "TFT forecast", "Temporal Fusion Transformer", "HF time series transformer", "probabilistic forecast with attention", "multi-horizon quantile forecast", "attention-based price forecast". For RNN baselines see `lstm-forecast`; for classical baselines see `arima-forecast`. Not for small datasets (<1000 timesteps) or single-series forecasting — use `lstm-forecast` or `arima-forecast` first.
license: Apache-2.0 (transformers), MIT (pytorch-forecasting)
metadata:
    skill-author: HyperFrequency
---

# Transformer Forecasting (HF Transformers + pytorch-forecasting TFT)

## When to use this skill

- You want a **probabilistic** forecast (samples from a learned distribution), not just a point estimate - use HF `TimeSeriesTransformerForPrediction`.
- You have **multiple related series + static + known-future covariates** (e.g. holidays, promos, regimes) and want interpretable attention - use `TemporalFusionTransformer` (TFT) from `pytorch-forecasting`.
- You need **quantile** outputs (P10/P50/P90) for risk-aware position sizing - TFT outputs quantiles natively.
- You want to compare an attention model against an LSTM (`lstm-forecast`) or ARIMA (`arima-forecast`) on the same split.

If you just need a quick recurrent baseline, use `lstm-forecast` first - transformers are heavier and underperform on small datasets.

## Install / setup

```bash
# HuggingFace path
uv add transformers torch accelerate gluonts huggingface_hub numpy pandas matplotlib

# pytorch-forecasting / TFT path (needs lightning >= 2.0)
uv add pytorch-forecasting lightning torch pandas numpy matplotlib
```

The HF time series models are minimal-from-config (no pretrained weights for arbitrary tickers) unless you fine-tune from `huggingface/time-series-transformer-tourism-monthly` or similar. TFT trains from scratch on your data.

## Minimal working example - HuggingFace TimeSeriesTransformer

This shows the *inference* shape contract clearly; full training uses a `gluonts`-style loader. Per the HF docs (`huggingface/transformers` model card), `past_values` length must equal `context_length + max(lags_sequence)`.

```python
import torch
from huggingface_hub import hf_hub_download
from transformers import TimeSeriesTransformerConfig, TimeSeriesTransformerForPrediction

# Option A - fine-tuned public checkpoint on monthly tourism data
model = TimeSeriesTransformerForPrediction.from_pretrained(
    "huggingface/time-series-transformer-tourism-monthly"
)

# Reusable demo batch (matches model's expected feature dims)
batch_file = hf_hub_download(
    repo_id="hf-internal-testing/tourism-monthly-batch",
    filename="train-batch.pt", repo_type="dataset",
)
batch = torch.load(batch_file)

# Training step - provide past + future
out = model(
    past_values=batch["past_values"],
    past_time_features=batch["past_time_features"],
    past_observed_mask=batch["past_observed_mask"],
    static_categorical_features=batch["static_categorical_features"],
    static_real_features=batch["static_real_features"],
    future_values=batch["future_values"],
    future_time_features=batch["future_time_features"],
)
out.loss.backward()                                       # NLL of the chosen distribution

# Inference - autoregressive sampling, no future_values
gen = model.generate(
    past_values=batch["past_values"],
    past_time_features=batch["past_time_features"],
    past_observed_mask=batch["past_observed_mask"],
    static_categorical_features=batch["static_categorical_features"],
    static_real_features=batch["static_real_features"],
    future_time_features=batch["future_time_features"],
)
# gen.sequences shape: (batch, num_parallel_samples, prediction_length)
mean_forecast    = gen.sequences.mean(dim=1)              # point forecast
p10, p50, p90    = torch.quantile(gen.sequences, torch.tensor([0.1, 0.5, 0.9]), dim=1)
```

For a from-scratch config (no pretrained), build it like this:

```python
config = TimeSeriesTransformerConfig(
    prediction_length=12,
    context_length=24,
    distribution_output="student_t",         # "student_t" | "normal" | "negative_binomial"
    lags_sequence=[1, 2, 3, 4, 5, 6, 7],
    num_time_features=2,                     # e.g. month-of-year, day-of-week
    num_static_categorical_features=1,
    cardinality=[100],                       # cardinality per static categorical
    embedding_dimension=[8],
)
model = TimeSeriesTransformerForPrediction(config)
```

## Minimal working example - Temporal Fusion Transformer (pytorch-forecasting)

```python
import numpy as np, pandas as pd
import lightning.pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting.metrics import QuantileLoss

# 1. Long-format dataframe: one row per (series, time)
rng = np.random.default_rng(0)
n_series, n_steps = 5, 400
rows = []
for sid in range(n_series):
    px = 100 + np.cumsum(rng.normal(0, 1, n_steps))
    for t, p in enumerate(px):
        rows.append({"series_id": str(sid), "time_idx": t, "y": p,
                     "month": (t % 12)})
df = pd.DataFrame(rows)

MAX_ENCODER = 60
MAX_PRED    = 10
cutoff = df["time_idx"].max() - MAX_PRED

training = TimeSeriesDataSet(
    df[df["time_idx"] <= cutoff],
    time_idx="time_idx",
    target="y",
    group_ids=["series_id"],
    max_encoder_length=MAX_ENCODER,
    max_prediction_length=MAX_PRED,
    static_categoricals=["series_id"],
    time_varying_known_reals=["time_idx", "month"],
    time_varying_unknown_reals=["y"],
)
validation = TimeSeriesDataSet.from_dataset(training, df, predict=True, stop_randomization=True)
train_dl = training.to_dataloader(train=True, batch_size=64, num_workers=0)
val_dl   = validation.to_dataloader(train=False, batch_size=64, num_workers=0)

# 2. Build TFT directly from the dataset's metadata
tft = TemporalFusionTransformer.from_dataset(
    training,
    learning_rate=0.03,
    hidden_size=32,
    attention_head_size=2,
    dropout=0.1,
    hidden_continuous_size=16,
    output_size=7,                 # 7 default quantiles
    loss=QuantileLoss(),
)

# 3. Train
trainer = pl.Trainer(
    max_epochs=10, accelerator="auto", gradient_clip_val=0.1,
    callbacks=[EarlyStopping(monitor="val_loss", patience=3, mode="min")],
)
trainer.fit(tft, train_dataloaders=train_dl, val_dataloaders=val_dl)

# 4. Predict - mode="prediction" returns the median; mode="quantiles" returns all 7
median_preds = tft.predict(val_dl, mode="prediction")
quantile_preds = tft.predict(val_dl, mode="quantiles")    # (n_samples, MAX_PRED, 7)
```

## Key API surface

| Library | Class / function | Purpose |
|---|---|---|
| transformers | `TimeSeriesTransformerConfig(prediction_length, context_length, lags_sequence, distribution_output, ...)` | Define architecture |
| transformers | `TimeSeriesTransformerForPrediction` | Encoder-decoder model with distribution head (NLL loss) |
| transformers | `model.generate(past_values=..., past_time_features=..., future_time_features=..., ...)` | Autoregressive sampling; returns `.sequences (batch, num_parallel_samples, prediction_length)` |
| pytorch-forecasting | `TimeSeriesDataSet(data, time_idx, target, group_ids, max_encoder_length, max_prediction_length, ...)` | Wraps long-format data for windowed training |
| pytorch-forecasting | `TemporalFusionTransformer.from_dataset(training, ...)` | Build TFT with architecture inferred from dataset |
| pytorch-forecasting | `tft.predict(dl, mode="prediction"|"quantiles"|"raw"|"samples", return_index=True)` | Inference |
| pytorch-forecasting | `pytorch_forecasting.metrics.QuantileLoss` / `SMAPE` / `MAE` | Loss functions |

## Evaluation

For probabilistic models report both point and interval metrics. The HF docs and pytorch-forecasting both recommend MAE/RMSE/MAPE on the median plus a coverage check on the prediction intervals.

```python
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Point metrics on the median
y_true = ...   # (N, H) ground truth
median = ...   # (N, H) median forecast

mae  = mean_absolute_error(y_true.ravel(), median.ravel())
rmse = np.sqrt(mean_squared_error(y_true.ravel(), median.ravel()))
mape = np.mean(np.abs((y_true - median) / np.maximum(np.abs(y_true), 1e-8))) * 100

# Interval coverage (target ~80% inside P10..P90)
p10, p90 = ...
coverage_80 = np.mean((y_true >= p10) & (y_true <= p90))
print(f"MAE {mae:.3f}  RMSE {rmse:.3f}  MAPE {mape:.2f}%  80%-coverage {coverage_80:.2%}")
```

For multi-horizon plots, compute the metric *per horizon step h* and visualise error-vs-horizon.

## Common pitfalls

1. **HF `past_values` length is NOT `context_length`.** Sequence length must be `context_length + max(lags_sequence)` (default 7). Truncating to `context_length` raises a shape error.
2. **HF model outputs samples, not a deterministic forecast.** `generate(...).sequences` has shape `(B, num_parallel_samples, prediction_length)`. Take `.mean(dim=1)` for a point forecast.
3. **Forgetting `past_time_features` / `future_time_features`.** Both are required even if `num_time_features=0` (use an `age` feature or zeros) - the model uses them as positional encoding.
4. **TFT `from_dataset` re-infers feature lists.** If you change static / known / unknown columns later, regenerate the `TimeSeriesDataSet` AND rebuild the model - mismatches at predict time silently mis-route variables.
5. **Long-format mistake.** `TimeSeriesDataSet` needs *long* format (`series_id, time_idx, y, covariates...`), not wide. A wide dataframe will train but treat each column as an independent target.
6. **TFT with one series.** TFT can work with `group_ids=[single_constant_id]` but variable selection collapses. With one series, use a vanilla transformer or `lstm-forecast`.
7. **Transformers are data-hungry.** With <1000 timesteps total they typically underperform ARIMA / LSTM. Use as a comparison baseline, not as a first reach.

## References

### Primary libraries
- [huggingface/transformers](https://github.com/huggingface/transformers) — issues, releases, model implementations (TimeSeriesTransformer lives in `src/transformers/models/time_series_transformer/`)
- [Transformers docs](https://huggingface.co/docs/transformers/) — pinned against the current stable channel (`v4.57` series at cross-check time)
- [sktime/pytorch-forecasting](https://github.com/sktime/pytorch-forecasting) — TFT, DeepAR, N-HiTS, N-BEATS, TiDE under one API
- [pytorch-forecasting readthedocs](https://pytorch-forecasting.readthedocs.io/) — current branch
- [pytorch-forecasting examples directory](https://github.com/sktime/pytorch-forecasting/tree/main/examples) — runnable scripts that mirror the docs
- [Lightning trainer docs](https://lightning.ai/docs/pytorch/stable/) — the training engine TFT plugs into

### Deep-dive docs (specific pages worth bookmarking)
- [HF Time Series Transformer model card](https://huggingface.co/docs/transformers/main/en/model_doc/time_series_transformer) — the `past_values` length contract (`context_length + max(lags_sequence)`) lives here
- [HF Informer](https://huggingface.co/docs/transformers/model_doc/informer) — Informer is the long-horizon cousin; useful when context length blows up
- [HF Autoformer](https://huggingface.co/docs/transformers/model_doc/autoformer) — series-decomposition variant, often a better default for strongly seasonal price data
- [HF PatchTST](https://huggingface.co/docs/transformers/model_doc/patchtst) — patch-based transformer; outperforms vanilla TST on many quant baselines
- [pytorch-forecasting `TimeSeriesDataSet`](https://pytorch-forecasting.readthedocs.io/en/stable/api/pytorch_forecasting.data.timeseries.TimeSeriesDataSet.html) — long-format contract; misuse here is the #1 silent failure mode
- [pytorch-forecasting `TemporalFusionTransformer`](https://pytorch-forecasting.readthedocs.io/en/stable/api/pytorch_forecasting.models.temporal_fusion_transformer.TemporalFusionTransformer.html) — the canonical TFT class reference
- [TFT interpretation tutorial](https://pytorch-forecasting.readthedocs.io/en/stable/tutorials/stallion.html) — variable-selection plots + attention heads (the whole point of TFT)
- [DeepAR in pytorch-forecasting](https://pytorch-forecasting.readthedocs.io/en/stable/api/pytorch_forecasting.models.deepar.DeepAR.html) — RNN baseline inside the same dataset abstraction
- [Tuner.lr_find / learning-rate finder](https://pytorch-forecasting.readthedocs.io/en/stable/) — TFT is sensitive to LR; the LR-finder is non-optional in practice

### Adjacent / alternative libraries
- [GluonTS](https://github.com/awslabs/gluonts) — Amazon's probabilistic forecasting library; HF TST uses GluonTS-style data contracts under the hood
- [NeuralForecast (Nixtla)](https://github.com/Nixtla/neuralforecast) — TFT, NHITS, PatchTST, Informer, Autoformer under one sklearn-style API
- [Darts](https://github.com/unit8co/darts) — easier on small datasets; ships TFT + NBEATS + Transformer in a single interface
- [lag-Llama](https://github.com/time-series-foundation-models/lag-llama) / [TimesFM](https://github.com/google-research/timesfm) — zero-shot foundation models when training data is scarce

### Academic papers
- Lim, B., Arık, S. Ö., Loeff, N., Pfister, T. (2021). "Temporal Fusion Transformers for interpretable multi-horizon time series forecasting." *International Journal of Forecasting* 37(4), 1748–1764. [arXiv:1912.09363](https://arxiv.org/abs/1912.09363) — the TFT paper; defines variable-selection networks, gated-residual networks, interpretable multi-head attention
- Salinas, D., Flunkert, V., Gasthaus, J., Januschowski, T. (2020). "DeepAR: Probabilistic forecasting with autoregressive recurrent networks." *International Journal of Forecasting* 36(3), 1181–1191. [arXiv:1704.04110](https://arxiv.org/abs/1704.04110) — probabilistic baseline that HF TST and pytorch-forecasting DeepAR both echo
- Vaswani, A. et al. (2017). "Attention Is All You Need." *NeurIPS 2017*. [arXiv:1706.03762](https://arxiv.org/abs/1706.03762) — the encoder-decoder skeleton TST inherits

### Tutorials & write-ups
- [HF blog: Probabilistic Time Series Forecasting with Transformers](https://huggingface.co/blog/time-series-transformers) — the canonical walkthrough of `TimeSeriesTransformerForPrediction` on the `monash_tsf/tourism_monthly` dataset
- [HF blog: Multivariate Probabilistic Forecasting](https://huggingface.co/blog/informer) — Informer for long-horizon multivariate
- [Stallion demand forecasting tutorial (TFT)](https://pytorch-forecasting.readthedocs.io/en/stable/tutorials/stallion.html) — end-to-end TFT with variable selection plots

### Standard datasets / benchmarks
- [Monash Time Series Forecasting Archive](https://forecastingdata.org/) — the de-facto benchmark; many HF / pytorch-forecasting examples use these CSVs
- [M4 / M5 Competitions](https://forecasters.org/resources/time-series-data/) — heavy retail / hierarchical baseline most papers compare against

### Last cross-checked
2026-05-20 — via Context7 `/huggingface/transformers` (v5.0.0 channel) + `/sktime/pytorch-forecasting`; Auggie not indexed for these repos.
