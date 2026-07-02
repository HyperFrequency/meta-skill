# ARIMA / SARIMA / Auto-ARIMA — References

Curated documentation, papers, and adjacent libraries for the `arima-forecast` skill.

## Primary libraries
- [statsmodels/statsmodels](https://github.com/statsmodels/statsmodels) — upstream repo (issues, releases, the canonical Python state-space implementation)
- [statsmodels stable docs](https://www.statsmodels.org/stable/) — pinned channel; the `dev` channel sometimes drops or renames keyword args between releases
- [alkaline-ml/pmdarima](https://github.com/alkaline-ml/pmdarima) — `auto_arima` (R's `auto.arima` port); now in maintenance mode (read the README before pinning Python 3.12+)
- [pmdarima docs](https://alkaline-ml.com/pmdarima/) — wrapper API reference

## Deep-dive docs (specific pages worth bookmarking)
- [`statsmodels.tsa.arima.model.ARIMA`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.arima.model.ARIMA.html) — the modern non-seasonal ARIMA class; supersedes the older `ARMA`/`ARIMA` in `tsa.arima_model`
- [`statsmodels.tsa.statespace.sarimax.SARIMAX`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html) — seasonal ARIMA + exogenous regressors; the workhorse for actual production quant ARIMA
- [`SARIMAXResults.get_forecast`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAXResults.get_forecast.html) — the result object that gives you `predicted_mean` + `conf_int`
- [State-space forecasting tutorial](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_forecasting.html) — official walkthrough of point + interval forecasts with `get_forecast`
- [SARIMAX & ARIMA — model specification notes](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_sarimax_stata.html) — replicates the Stata SARIMAX examples; useful when sanity-checking econometric papers
- [`statsmodels.tsa.stattools.adfuller`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html) and [`kpss`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.kpss.html) — stationarity tests you must run before picking `d`
- [`pmdarima.arima.auto_arima`](https://alkaline-ml.com/pmdarima/modules/generated/pmdarima.arima.auto_arima.html) — stepwise + parallel-grid search over `(p,d,q)(P,D,Q,s)`; the doc page lists every search-shape knob
- [`pmdarima.arima.ARIMA.update`](https://alkaline-ml.com/pmdarima/modules/generated/pmdarima.arima.ARIMA.html#pmdarima.arima.ARIMA.update) — append new observations without a full refit; the cheap path for rolling-origin evaluation

## Adjacent / alternative libraries
- [StatsForecast (Nixtla)](https://github.com/Nixtla/statsforecast) — much faster `AutoARIMA` (Numba JIT), the same model class but ~10–50× quicker on large panels
- [`darts`](https://github.com/unit8co/darts) — `ARIMA` / `AutoARIMA` / `KalmanForecaster` next to LSTM/TFT in one API; useful for head-to-head bake-offs
- [Prophet](https://github.com/facebook/prophet) — when seasonality/holidays dominate and you don't need ARIMA's strict assumptions (see `prophet-forecast` skill)
- [`sktime`](https://github.com/sktime/sktime) — wraps statsmodels + pmdarima behind a sklearn-compatible time-series API

## Academic papers
- Box, G. E. P. & Jenkins, G. M. (1970). *Time Series Analysis: Forecasting and Control*. Holden-Day — the canonical reference for the ARIMA methodology; modern editions co-authored with Reinsel and Ljung
- Hyndman, R. J. & Khandakar, Y. (2008). "Automatic Time Series Forecasting: The forecast Package for R." *Journal of Statistical Software* 27(3). [doi:10.18637/jss.v027.i03](https://doi.org/10.18637/jss.v027.i03) — the `auto.arima` algorithm that `pmdarima` ports

## Tutorials & write-ups
- [Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* (3rd ed., free online)](https://otexts.com/fpp3/) — Chapters 8–9 cover ARIMA / SARIMA end-to-end; the de facto textbook
- [statsmodels SARIMAX with exogenous regressors](https://www.statsmodels.org/stable/examples/notebooks/generated/statespace_arima_0.html) — practical pattern for adding `exog` (regime dummies, macro factors)

## Last cross-checked
2026-05-20 — via Context7 `/websites/statsmodels_stable` (29k snippets, the most complete) + `/alkaline-ml/pmdarima` (231 snippets); Auggie not indexed.
