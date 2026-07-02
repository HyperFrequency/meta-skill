---
name: prophet-forecast
version: 0.1.0
description: Meta Prophet for additive trend + multi-seasonality + holiday-aware time series forecasting. Trigger on phrases like "fit Prophet", "Facebook Prophet", "seasonal forecast with holidays", "weekly + yearly seasonality forecast", "add holiday effects", "Prophet cross_validation", "prophet uncertainty intervals", or when the user has daily/weekly business-style series with strong calendar effects. Use as a robust seasonal baseline. For deeper RNN / transformer models see `lstm-forecast` / `transformer-forecast`. For pure stochastic-process models see `arima-forecast`. Not for sub-daily tick data or regime-switching series — use LSTM or ARIMA instead.
license: MIT
metadata:
    skill-author: HyperFrequency
---

# Prophet: Trend + Seasonality + Holidays Forecasting

## When to use this skill

- Daily, weekly, or monthly business-style series with **strong seasonality** (intraweek, intrayear).
- Series with **known holiday / event effects** you can encode as a calendar.
- You want a **fast, robust baseline** that handles missing days, outliers, and changepoints with minimal tuning.
- You want **uncertainty intervals** out of the box without writing your own MCMC.

Prophet is *not* a good fit for sub-daily price tick data, regime-switching series, or pure random walks - those need ARIMA / LSTM / TFT.

## Install / setup

```bash
uv add prophet pandas numpy matplotlib
# or: pip install prophet
```

Prophet ships its own Stan backend (cmdstanpy by default) - first import compiles it. On Apple Silicon and Linux this is one-time and silent; on Windows pre-installed VC++ build tools are required.

## Minimal working example

Prophet requires a 2-column dataframe named **exactly** `ds` (datestamp) and `y` (value).

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics
from sklearn.metrics import mean_absolute_error, mean_squared_error

# 1. Load -> rename to ds, y
url = ("https://raw.githubusercontent.com/facebook/prophet/main/"
       "examples/example_wp_log_peyton_manning.csv")
df = pd.read_csv(url)                              # already has ds, y
assert set(df.columns) >= {"ds", "y"}

# Chronological train/test split
split = int(0.9 * len(df))
train_df, test_df = df.iloc[:split], df.iloc[split:]

# 2. Fit
m = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=False,
    seasonality_mode="additive",        # use "multiplicative" if variance grows with level
    interval_width=0.8,                 # 80% uncertainty intervals
)
m.add_country_holidays(country_name="US")
m.fit(train_df)

# 3. Forecast (must call make_future_dataframe even for in-sample predict)
future = m.make_future_dataframe(periods=len(test_df), freq="D")
forecast = m.predict(future)
print(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail())

# 4. Evaluate on the held-out tail
merged = forecast.merge(test_df, on="ds", how="inner")
mae  = mean_absolute_error(merged["y"], merged["yhat"])
rmse = np.sqrt(mean_squared_error(merged["y"], merged["yhat"]))
print(f"holdout MAE {mae:.3f}  RMSE {rmse:.3f}")

# 5. Plots
m.plot(forecast); plt.title("Forecast"); plt.show()
m.plot_components(forecast); plt.show()             # trend, weekly, yearly, holidays
```

## Cross-validation (rolling-origin)

Prophet has a built-in expanding-window CV. Use it for honest out-of-sample evaluation:

```python
from prophet.diagnostics import cross_validation, performance_metrics
from prophet.plot import plot_cross_validation_metric

df_cv = cross_validation(
    m,
    initial="730 days",       # initial training window
    period="180 days",        # space between successive cutoffs
    horizon="365 days",       # forecast length per cutoff
    parallel="processes",     # "processes" | "threads" | "dask" | None
)
# df_cv columns: ds, yhat, yhat_lower, yhat_upper, y, cutoff

df_p = performance_metrics(df_cv, rolling_window=0.1)
print(df_p[["horizon", "mae", "rmse", "mape", "coverage"]].head())

fig = plot_cross_validation_metric(df_cv, metric="mape"); plt.show()
```

## Key API surface

| Class / function | Purpose |
|---|---|
| `Prophet(growth="linear"|"logistic"|"flat", changepoint_prior_scale=0.05, seasonality_mode="additive"|"multiplicative", interval_width=0.8)` | Model constructor |
| `m.add_seasonality(name, period, fourier_order, condition_name=None)` | Custom seasonality (e.g. monthly with `period=30.5, fourier_order=5`) |
| `m.add_regressor(name, mode="additive"|"multiplicative", standardize="auto")` | Add an extra time-varying regressor (column must exist in train + future df) |
| `m.add_country_holidays(country_name)` | Built-in holiday calendars (US, UK, IN, etc.) |
| `m.fit(df)` | Fit MAP by default; pass `mcmc_samples=300` for full posterior |
| `m.make_future_dataframe(periods, freq="D", include_history=True)` | Build the ds index for prediction |
| `m.predict(future_df)` | Returns `yhat`, `yhat_lower`, `yhat_upper` + components |
| `prophet.diagnostics.cross_validation(m, initial, period, horizon, parallel)` | Rolling-origin CV |
| `prophet.diagnostics.performance_metrics(df_cv, rolling_window=0.1)` | MSE / RMSE / MAE / MAPE / SMAPE / coverage by horizon |
| `prophet.serialize.model_to_json(m)` / `model_from_json(s)` | Persist a fitted model |

## Evaluation

```python
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

mae  = mean_absolute_error(merged["y"], merged["yhat"])
rmse = np.sqrt(mean_squared_error(merged["y"], merged["yhat"]))
mape = np.mean(np.abs((merged["y"] - merged["yhat"]) / np.maximum(np.abs(merged["y"]), 1e-8))) * 100
coverage = ((merged["y"] >= merged["yhat_lower"]) & (merged["y"] <= merged["yhat_upper"])).mean()

print(f"MAE {mae:.3f}  RMSE {rmse:.3f}  MAPE {mape:.2f}%  coverage {coverage:.2%}")

# Residuals
import matplotlib.pyplot as plt
resid = merged["y"] - merged["yhat"]
fig, ax = plt.subplots(1, 2, figsize=(10, 3))
ax[0].plot(merged["ds"], resid); ax[0].axhline(0, color="r")
ax[1].hist(resid, bins=30)
plt.show()
```

Coverage near `interval_width` (e.g. ~0.8 for `interval_width=0.8`) means intervals are well-calibrated. Under-coverage = intervals too tight, over-coverage = too wide.

## Common pitfalls

1. **Column names must be `ds` and `y` literally.** Not `date`, `Date`, `timestamp`, or `value`. Rename first: `df.rename(columns={"date":"ds","close":"y"})`.
2. **`ds` must be datetime, not string.** `pd.to_datetime(df["ds"])` before fitting, or Prophet silently treats it as object and seasonality is wrong.
3. **`changepoint_prior_scale` is the most important knob.** Default 0.05 is conservative. If the forecast looks too flat, raise to 0.1-0.5. If overfit, drop to 0.01.
4. **`make_future_dataframe(periods=N)` extends from the last `ds`, not from "today".** If your data ends in 2024 and you call `periods=30`, you get forecasts for early 2024, not into the present.
5. **Holiday windows leak into `add_regressor`.** If you add both `add_country_holidays("US")` and a hand-rolled `is_holiday` regressor, the model fits the effect twice. Pick one.
6. **`growth="logistic"` requires `cap` (and optionally `floor`).** Add them to both the training df and the future df, else fit fails.
7. **MCMC mode (`mcmc_samples > 0`) is slow.** ~minutes for hundreds of samples. Only enable when you need posterior intervals on the seasonal components, not just point forecasts.
8. **`cross_validation(parallel="processes")` on Jupyter Windows.** Falls back silently due to fork constraints - use `parallel="threads"` or run from a `.py` script.

## References

### Primary library
- [facebook/prophet](https://github.com/facebook/prophet) — upstream repo (issues, releases, the R + Python packages share a Stan model)
- [Prophet docs (current)](https://facebook.github.io/prophet/) — cross-checked against `prophet>=1.1` (cmdstanpy backend)
- [Quick start](https://facebook.github.io/prophet/docs/quick_start.html) — minimal `ds`/`y` workflow
- [Prophet `examples/`](https://github.com/facebook/prophet/tree/main/examples) — canonical Peyton-Manning + retail CSVs the docs use
- [Release notes](https://github.com/facebook/prophet/releases) — note `pystan` → `cmdstanpy` migration around 1.0

### Deep-dive docs (specific pages worth bookmarking)
- [Trend changepoints](https://facebook.github.io/prophet/docs/trend_changepoints.html) — `changepoint_prior_scale`, `changepoint_range`, manual `changepoints=[...]`; the single most useful tuning lever for noisy price data
- [Seasonality, holiday effects, and regressors](https://facebook.github.io/prophet/docs/seasonality,_holiday_effects,_and_regressors.html) — `add_seasonality`, `add_country_holidays`, `add_regressor`; covers multiplicative vs additive mode and the seasonality+holidays double-count footgun
- [Saturating forecasts](https://facebook.github.io/prophet/docs/saturating_forecasts.html) — `growth="logistic"` with `cap` (and optional `floor`); the only sane mode for bounded series (interest rates near zero, capacity-limited demand)
- [Outliers](https://facebook.github.io/prophet/docs/outliers.html) — how Prophet treats outliers as missing (`y=NaN`) instead of trying to fit them — a quant-grade pattern for treating earnings-day jumps
- [Diagnostics](https://facebook.github.io/prophet/docs/diagnostics.html) — `cross_validation`, `performance_metrics`, and the rolling-origin CV semantics
- [Uncertainty intervals](https://facebook.github.io/prophet/docs/uncertainty_intervals.html) — `mcmc_samples` for posterior intervals on seasonal components vs analytic intervals from MAP
- [Non-daily data](https://facebook.github.io/prophet/docs/non-daily_data.html) — hourly, sub-daily, monthly — when to override `daily_seasonality` / `weekly_seasonality` / `yearly_seasonality`

### Adjacent / alternative libraries
- [NeuralProphet](https://github.com/ourownstory/neural_prophet) — PyTorch port + AR-Net hybrid; useful when Prophet's additive structure isn't expressive enough for autoregressive dynamics
- [Prophetverse](https://github.com/felipeangelimvieira/prophetverse) — PyMC / numpyro Bayesian extension with custom priors and non-linear regressors
- [StatsForecast (Nixtla)](https://github.com/Nixtla/statsforecast) — much faster ETS/ARIMA/Theta baselines you should benchmark Prophet against
- [modeltime](https://github.com/business-science/modeltime) — R / tidymodels ecosystem version when you want Prophet next to ARIMA / ETS / XGBoost in one workflow

### Academic papers
- Taylor, S. J. & Letham, B. (2018). "Forecasting at Scale." *The American Statistician* 72(1), 37–45. [doi:10.1080/00031305.2017.1380080](https://doi.org/10.1080/00031305.2017.1380080) — the Prophet paper; defines the additive `y(t) = g(t) + s(t) + h(t) + ε` decomposition the library implements

### Tutorials & write-ups
- [Prophet R API docs](https://facebook.github.io/prophet/docs/installation.html#r) — useful when comparing parameter names across the R / Python packages
- [`add_country_holidays` country list](https://github.com/facebook/prophet/blob/main/python/prophet/make_holidays.py) — read this before assuming your jurisdiction is covered; gaps are common for emerging markets

### Last cross-checked
2026-05-20 — via Context7 `/facebook/prophet` (648 snippets) + `/websites/facebook_github_io_prophet`; Auggie not indexed.
