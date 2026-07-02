---
name: arima-forecast
version: 0.1.0
description: ARIMA / SARIMA / SARIMAX forecasting via `statsmodels.tsa.arima.model.ARIMA` + `statsmodels.tsa.statespace.SARIMAX`, plus auto-ARIMA order selection via `pmdarima.auto_arima`. Trigger on phrases like "fit ARIMA", "SARIMA forecast", "auto-ARIMA", "stationarity test", "ADF / KPSS check", "ACF / PACF identification", "Box-Jenkins", "seasonal ARIMA", "AR(p) MA(q)", "differencing order". Use as the canonical classical baseline for any univariate price/return series. For neural models see `lstm-forecast` / `transformer-forecast`; for additive trend + seasonality see `prophet-forecast`.
license: BSD-3-Clause (statsmodels), MIT (pmdarima)
metadata:
    skill-author: HyperFrequency
---

# ARIMA / SARIMA / Auto-ARIMA Forecasting

## When to use this skill

- You want a classical Box-Jenkins baseline (`ARIMA(p, d, q)`) before reaching for deep learning.
- Your series has seasonality and you want **`SARIMA(p, d, q)(P, D, Q, m)`** with explicit seasonal terms.
- You have **exogenous regressors** (rates, volume, sentiment) - use `SARIMAX`.
- You don't want to hand-pick `(p, d, q)` - use `pmdarima.auto_arima` for stepwise AIC search.

If you need additive seasonality + holidays out of the box, prefer `prophet-forecast`. If you need attention / multi-series / static covariates, jump to `transformer-forecast`.

## Install / setup

```bash
uv add statsmodels pmdarima pandas numpy matplotlib scikit-learn
```

`pmdarima` ships pre-built wheels for common platforms; if it fails to build on Python 3.12+ on macOS arm64, use Python 3.11 or check the upstream issue tracker (the project is in maintenance mode as of 2024).

## Minimal working example - statsmodels SARIMAX

```python
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from sklearn.metrics import mean_absolute_error, mean_squared_error

# 1. Load a series with a datetime index
rng = pd.date_range("2018-01-01", periods=600, freq="D")
y = pd.Series(
    100 + np.cumsum(np.random.default_rng(0).normal(0, 1, 600))
    + 5 * np.sin(2 * np.pi * np.arange(600) / 30),
    index=rng, name="close",
)

# 2. Stationarity check (ADF). Null = unit root (non-stationary).
adf_p = adfuller(y)[1]
print(f"ADF p-value (raw): {adf_p:.4f}  -> differenced if > 0.05")

# 3. Identify (p, q) and (P, Q) visually
fig, ax = plt.subplots(2, 1, figsize=(9, 5))
plot_acf(y.diff().dropna(), lags=40, ax=ax[0])
plot_pacf(y.diff().dropna(), lags=40, ax=ax[1])
plt.show()

# 4. Train/test split (chronological!)
split = int(0.9 * len(y))
y_tr, y_te = y.iloc[:split], y.iloc[split:]

# 5. Fit SARIMA(1,1,1)(1,1,1,7)  -- weekly seasonality m=7
model = SARIMAX(
    y_tr,
    order=(1, 1, 1),
    seasonal_order=(1, 1, 1, 7),
    enforce_stationarity=False,
    enforce_invertibility=False,
)
res = model.fit(disp=False)
print(res.summary())

# 6. Forecast with prediction intervals
fc = res.get_forecast(steps=len(y_te))
mean_fc = fc.predicted_mean
ci = fc.conf_int(alpha=0.05)               # 95% intervals

# 7. Evaluate
mae  = mean_absolute_error(y_te, mean_fc)
rmse = np.sqrt(mean_squared_error(y_te, mean_fc))
print(f"holdout MAE {mae:.3f}  RMSE {rmse:.3f}")

# 8. Plot
fig, ax = plt.subplots(figsize=(10, 4))
y_tr.iloc[-90:].plot(ax=ax, label="train tail")
y_te.plot(ax=ax, label="test")
mean_fc.plot(ax=ax, label="forecast", style="--")
ax.fill_between(ci.index, ci.iloc[:, 0], ci.iloc[:, 1], alpha=0.2)
ax.legend(); plt.show()

# 9. Residual diagnostics
res.plot_diagnostics(figsize=(11, 7)); plt.show()
```

## Minimal working example - auto-ARIMA via pmdarima

`auto_arima` runs a stepwise AIC search over `(p, d, q) x (P, D, Q, m)` with stationarity tests for `d` and seasonality tests for `D`. Use it when you don't want to eyeball ACF/PACF.

```python
import pmdarima as pm
from pmdarima.model_selection import train_test_split
import numpy as np

# pmdarima ships sample series
y = pm.datasets.load_wineind()              # 176 monthly wine sales obs
train, test = train_test_split(y, train_size=150)

auto = pm.auto_arima(
    train,
    start_p=1, start_q=1, max_p=3, max_q=3,
    m=12,                            # seasonal period (monthly -> 12)
    seasonal=True,
    d=None,                          # let KPSS choose d
    D=None,                          # let OCSB choose D
    test="kpss",
    seasonal_test="ocsb",
    stepwise=True,                   # fast stepwise search
    suppress_warnings=True,
    error_action="ignore",
    trace=False,
    information_criterion="aic",
)
print(auto.summary())

# Forecast + 95% CI
fc, ci = auto.predict(n_periods=len(test), return_conf_int=True, alpha=0.05)
print(f"MAE {np.mean(np.abs(test - fc)):.2f}  "
      f"RMSE {np.sqrt(np.mean((test - fc) ** 2)):.2f}")

# Continue training online with new observations (state preserved)
auto.update(test[:5])                # incorporates 5 new points
new_fc = auto.predict(n_periods=10)
```

## Key API surface

| Library | Class / function | Purpose |
|---|---|---|
| statsmodels | `statsmodels.tsa.arima.model.ARIMA(endog, order=(p,d,q))` | Non-seasonal ARIMA |
| statsmodels | `statsmodels.tsa.statespace.sarimax.SARIMAX(endog, exog=None, order, seasonal_order=(P,D,Q,m))` | Seasonal ARIMA + exogenous regressors (preferred general API) |
| statsmodels | `results.get_forecast(steps).predicted_mean`, `.conf_int(alpha=0.05)`, `.summary_frame()` | Out-of-sample forecast + intervals |
| statsmodels | `results.plot_diagnostics()` | Standard residual diagnostic 4-panel |
| statsmodels | `statsmodels.tsa.stattools.adfuller(y)` / `kpss(y)` | Stationarity tests |
| statsmodels | `statsmodels.graphics.tsaplots.plot_acf` / `plot_pacf` | Order identification |
| pmdarima | `pmdarima.auto_arima(y, m=, seasonal=, stepwise=, information_criterion="aic")` | Automatic order selection |
| pmdarima | `pmdarima.arima.utils.ndiffs(y, test="kpss")` / `nsdiffs(y, m, test="ch")` | Recommended `d` / `D` for given test |
| pmdarima | `model.predict(n_periods, return_conf_int=True)` / `model.update(new_y)` | Forecast + online state update |
| pmdarima | `pm.model_selection.train_test_split(y, train_size=)` | Chronological split helper |

## Evaluation

```python
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.stats.diagnostic import acorr_ljungbox

mae  = mean_absolute_error(y_te, mean_fc)
rmse = np.sqrt(mean_squared_error(y_te, mean_fc))
mape = np.mean(np.abs((y_te.values - mean_fc.values) / np.maximum(np.abs(y_te.values), 1e-8))) * 100

# Coverage of 95% CI
covered = ((y_te.values >= ci.iloc[:, 0].values) & (y_te.values <= ci.iloc[:, 1].values)).mean()
print(f"MAE {mae:.3f}  RMSE {rmse:.3f}  MAPE {mape:.2f}%  95%-coverage {covered:.2%}")

# Residual whiteness (Ljung-Box on the fitted residuals)
lb = acorr_ljungbox(res.resid, lags=[10, 20], return_df=True)
print(lb)                          # p > 0.05 on all lags = residuals look like white noise
```

A good ARIMA has:
- Ljung-Box `p > 0.05` (residual autocorrelation absent)
- Roughly normal residual histogram + Q-Q
- 95% interval coverage close to 0.95 out-of-sample

## Common pitfalls

1. **Non-stationary data fitted with `d=0`.** Run ADF + KPSS first. If ADF `p > 0.05`, set `d=1` (or higher). Or just let `auto_arima(d=None)` decide.
2. **`SARIMAX` index without a frequency.** Pass a pandas `DatetimeIndex` with `.freq` set (e.g. `"D"`, `"W"`, `"M"`), otherwise `get_forecast(steps=N)` works but date alignment in plots breaks.
3. **Picking the wrong `m`.** Monthly data: `m=12`. Daily data with weekly seasonality: `m=7`. Hourly data with daily seasonality: `m=24`. `m=1` disables seasonality.
4. **`auto_arima(stepwise=False)` on long series.** Exhaustive search is `O(max_p * max_q * max_P * max_Q)` fits and can take hours. Keep `stepwise=True` unless you're explicitly benchmarking.
5. **Refitting on every test step.** `pmdarima` has `model.update(new_obs)` which only updates state - much cheaper than a full refit. Use it for rolling-origin evaluation.
6. **Treating `predicted_mean` as the truth on log-transformed series.** If you logged `y` first, `np.exp(predicted_mean)` is *biased* (Jensen's inequality). Add `+ 0.5 * predicted_var` before exponentiating, or forecast on the level directly.
7. **`SARIMAX` with too many seasonal terms.** `(1, 1, 1)(1, 1, 1, 12)` is ~6 params plus variance; pushing to `(3, 1, 3)(2, 1, 2, 12)` often over-fits and explodes the CI. Use AIC + holdout MAE together.
8. **`pmdarima` end-of-life signal.** The repo is in maintenance mode (Python 3.12+ wheels have lagged); if you need cutting-edge Python, fall back to plain `statsmodels.SARIMAX` with a small AIC-grid loop.

## References

Full reference list — primary libraries, deep-dive doc pages, adjacent libraries (StatsForecast, darts, sktime), academic papers (Box-Jenkins, Hyndman-Khandakar), and tutorials (fpp3) — lives in [`references/sources.md`](references/sources.md).

Quick entry points:
- [statsmodels stable docs](https://www.statsmodels.org/stable/) — `ARIMA`, `SARIMAX`, stationarity tests, ACF/PACF
- [pmdarima docs](https://alkaline-ml.com/pmdarima/) — `auto_arima` + online `update` (maintenance mode; check wheels for Python 3.12+)

Last cross-checked 2026-05-20 via Context7 `/websites/statsmodels_stable` + `/alkaline-ml/pmdarima`.
