---
name: garch-volatility
version: 0.1.0
description: GARCH-family volatility modeling via the arch library. Use when you need to model time-varying conditional variance of financial returns, capture volatility clustering and asymmetric leverage effects, or forecast variance with GARCH(1,1), GJR-GARCH, EGARCH, TARCH, or APARCH. Best for univariate financial return series where heteroskedasticity dominates. For multivariate volatility consider DCC/BEKK (not in arch); for stochastic volatility use pymc. Not for realized-volatility or high-frequency estimators (use pyfin/mfe-toolbox instead).
allowed-tools: Bash, Read, Edit, Write
license: NCSA-style (see arch repo)
metadata:
    skill-author: HyperFrequency
---

# GARCH Volatility Modeling with arch

## Overview

The `arch` library (Kevin Sheppard, University of Oxford) is the canonical Python implementation of GARCH-family volatility models with Cython + Numba acceleration. Use this skill to fit, diagnose, and forecast conditional variance models on financial return series: standard GARCH(1,1), GJR-GARCH (leverage effects), EGARCH (log-variance / asymmetry), TARCH (threshold ARCH), and APARCH (asymmetric power ARCH). Also covers unit root tests, bootstrap methods, and HAR-RV models, but this skill focuses on volatility.

## When to Use This Skill

This skill should be used when:
- Modeling volatility clustering in daily / intraday equity, FX, crypto returns
- Computing time-varying variance for risk management (input to VaR, Sharpe ratio, position sizing)
- Forecasting next-day conditional variance (`h_{t+1}`) for option pricing or vol targeting
- Testing for asymmetric volatility ("leverage effect": negative shocks raise variance more than positive)
- Comparing volatility model families via AIC/BIC, log-likelihood, or out-of-sample MSE
- Producing standardized residuals for downstream copula / dependence modeling

Don't use for: multivariate volatility (use `rmgarch` in R or `mgarch` packages), realized-volatility / high-frequency estimators (use `arch.unitroot` is not it — consider `pyfin`/`mfe-toolbox`), or stochastic-volatility models (use `pymc` / `numpyro`).

## Install / Setup

```bash
pip install arch
# or, if you need optimized linear algebra:
pip install 'arch[recommended]'
```

Verify:

```python
import arch
print(arch.__version__)  # 7.x as of 2025
```

`arch` depends on `numpy`, `scipy`, `pandas`, `statsmodels`. Cython extensions compile during install (or use prebuilt wheels).

## Minimal Example — Fit GARCH(1,1) and Forecast Variance

```python
import numpy as np
import pandas as pd
from arch import arch_model

# IMPORTANT: arch expects returns in PERCENT (e.g. 1.5 means 1.5%), not decimals.
# Daily log returns of ~0.01 should be scaled to ~1.0 before fitting.
# Otherwise the optimizer struggles and you'll get a `DataScaleWarning`.
rng = np.random.default_rng(42)
returns_decimal = rng.standard_normal(2000) * 0.012      # synthetic daily returns
returns_pct = returns_decimal * 100                       # scale to percent

# arch_model defaults: mean='Constant', vol='GARCH', dist='Normal', p=1, q=1
am = arch_model(returns_pct, mean='Constant', vol='GARCH', p=1, q=1, dist='normal')
res = am.fit(disp='off')
print(res.summary())

# Persistence check (stationarity of conditional variance):
alpha = res.params['alpha[1]']
beta  = res.params['beta[1]']
persistence = alpha + beta
print(f"alpha + beta = {persistence:.4f}  (should be < 1.0 for covariance-stationary)")

# In-sample conditional variance series:
cond_var = res.conditional_volatility ** 2

# 5-step-ahead variance forecast (analytic by default for GARCH):
fcast = res.forecast(horizon=5, reindex=False)
print("Variance forecasts (h+1 ... h+5):")
print(fcast.variance.iloc[-1].values)
```

For asymmetric models, swap the volatility spec:

```python
# GJR-GARCH(1,1,1) — adds an asymmetric `o` term capturing leverage
gjr = arch_model(returns_pct, vol='GARCH', p=1, o=1, q=1, dist='t').fit(disp='off')

# EGARCH(1,1,1) — log-variance, no parameter-positivity constraints
egarch = arch_model(returns_pct, vol='EGARCH', p=1, o=1, q=1, dist='t').fit(disp='off')
```

## Key API Surface

| Object / function | Purpose |
|---|---|
| `arch_model(y, mean=..., vol=..., p, o, q, dist=...)` | Top-level convenience builder; returns a `ARCHModel` instance |
| `am.fit(update_freq=N, disp='off')` | MLE via L-BFGS-B; returns `ARCHModelResult` |
| `res.summary()` | Coefficient table with std errors, t-stats, AIC/BIC |
| `res.params` | `pd.Series` of fitted params (`mu`, `omega`, `alpha[1]`, `beta[1]`, …) |
| `res.conditional_volatility` | In-sample sigma_t series (note: volatility, not variance) |
| `res.std_resid` | Standardized residuals (epsilon_t / sigma_t), used for copula / VaR backtests |
| `res.forecast(horizon=H, method='analytic'\|'simulation'\|'bootstrap')` | Returns `.mean`, `.variance`, `.residual_variance` |
| `arch.univariate.ConstantMean / ZeroMean / ARX` | Mean models, composable with volatility |
| `arch.univariate.GARCH / EGARCH / APARCH / FIGARCH / HARCH` | Volatility specs |
| `dist='normal'\|'t'\|'skewt'\|'ged'` | Error distribution; fat-tailed `'t'` or `'skewt'` are usually better for daily returns |

## Interpreting the Output

**Coefficient table** — what to look for in `res.summary()`:

- `omega > 0`, `alpha[i] >= 0`, `beta[j] >= 0` — required for variance positivity in plain GARCH. EGARCH has no such constraint (it models log-variance).
- `alpha[1] + beta[1] < 1` — **covariance stationarity**. Above 1, the model is "explosive" and variance forecasts diverge. Right at 1 is IGARCH (integrated GARCH).
- Typical equity daily values: `alpha ~ 0.05–0.15`, `beta ~ 0.80–0.92`, persistence `~ 0.97–0.99` (high but stationary).
- For GJR / TARCH: `gamma[1] > 0` and significant ⇒ leverage effect present (bad news raises variance more than good news).
- For EGARCH: a significant negative `gamma[1]` ⇒ same leverage interpretation (sign convention flipped).

**Goodness of fit** — compare nested or non-nested models via:

- AIC / BIC (lower is better; BIC penalizes more, favoring parsimony)
- Log-likelihood (`res.loglikelihood`) — strictly higher with more parameters, so only useful with a likelihood-ratio test
- Standardized-residual diagnostics: Ljung-Box on `res.std_resid` should be insignificant (no remaining autocorrelation); Ljung-Box on `res.std_resid ** 2` should be insignificant (no remaining ARCH effects)

**Forecast objects** — `res.forecast(horizon=H, reindex=False)` returns a `ARCHModelForecast` with:
- `.mean` (n_obs x H) — conditional mean forecast
- `.variance` (n_obs x H) — conditional variance forecast (NOT volatility)
- `.residual_variance` — variance of residuals (differs from `.variance` only for ARX mean specs)

Use `method='simulation'` or `'bootstrap'` for non-analytic forecast horizons (e.g. when the variance equation has asymmetry that doesn't admit a closed form beyond h=1).

## Workflow: From Raw Returns to Volatility-Adjusted VaR

A canonical end-to-end pipeline that ties this skill to downstream risk work:

```python
import numpy as np
import pandas as pd
from arch import arch_model
from scipy.stats import t as student_t

# 1. Pre-clean: log returns, scale to percent, drop NaNs.
prices = pd.Series(...)  # your price series
log_ret_pct = 100 * np.log(prices / prices.shift(1)).dropna()

# 2. Optional ARMA pre-filtering if returns are autocorrelated.
#    Lightweight: just check qs.stats.autocorr or statsmodels Ljung-Box first.

# 3. Fit GJR-GARCH with Student-t innovations (a good default for equities).
am = arch_model(log_ret_pct, mean='Constant', vol='GARCH', p=1, o=1, q=1, dist='t')
res = am.fit(disp='off')

# 4. Diagnostic checks:
print("Persistence:", res.params.get('alpha[1]', 0) + res.params.get('beta[1]', 0)
                      + 0.5 * res.params.get('gamma[1]', 0))  # GJR persistence
print("Nu (Student-t df):", res.params.get('nu', np.nan))     # df < 6 = heavy tails

# 5. Forecast 1-step ahead conditional volatility.
fcast = res.forecast(horizon=1, reindex=False)
sigma_next = float(np.sqrt(fcast.variance.iloc[-1, 0]))   # in PERCENT
nu = res.params['nu']

# 6. Conditional 1-day 99% VaR using the Student-t quantile.
#    Returns negative for losses.
var_99_pct = student_t.ppf(0.01, df=nu) * sigma_next        # in PERCENT
print(f"Conditional 1-day 99% VaR: {var_99_pct:.3f}%")
```

Why GJR-GARCH-t: GJR captures leverage (cheap and significant for equities); Student-t innovations capture remaining fat tails that GARCH alone won't.

## Choosing Between GARCH Variants

| Spec | When to choose | Cost |
|---|---|---|
| `GARCH(1,1)` | Default for "tell me the conditional vol." Symmetric. | Cheapest, often "good enough" |
| `GJR-GARCH(1,1,1)` | Equities, anything with leverage effect | One extra param; usually beats GARCH on equity data |
| `EGARCH(1,1,1)` | Want log-variance (no positivity constraints) or strong asymmetry | Slightly slower; mildly harder optimizer |
| `TARCH(1,1,1)` | Threshold ARCH; same role as GJR but on volatility scale (power=1) | Similar to GJR |
| `APARCH(1,1,1)` | Want to *estimate* the power exponent rather than fix it | More parameters; can be unstable |
| `FIGARCH` | Long-memory volatility (e.g. realized variance) | Slow optimization |

Rule of thumb: start with `GARCH(1,1) + dist='t'`. If AIC drops materially under `o=1`, you have leverage — go to GJR. If signs of long memory in `std_resid ** 2` ACF (slow decay), consider FIGARCH or HAR-RV.

## Common Pitfalls

1. **Returns in decimals instead of percent.** `arch` is calibrated for returns in percent (e.g. `1.5` for 1.5%). Passing decimals (`0.015`) triggers `DataScaleWarning` and frequently causes optimizer convergence failures or absurd `omega` estimates. **Fix:** multiply by 100 before fitting, or set `rescale=True` and let `arch` handle it (but read the rescaled summary carefully — `omega` and forecasts come back on the original scale).
2. **Forgetting `dist='t'` on fat-tailed series.** The Normal distribution underestimates tail probability for daily equity / crypto returns. Switch to `dist='t'` or `dist='skewt'` and you'll usually see a sharp log-likelihood improvement and more honest VaR estimates downstream. Symptom of Normal-misspecification: large Jarque-Bera p-value on `std_resid`, plus a bunched left tail in the QQ plot.
3. **Persistence at or above 1.** If `alpha + beta >= 1`, multi-step variance forecasts will not mean-revert. Consider IGARCH (constrain to 1) or check for structural breaks / outliers (e.g. COVID March 2020 in equity series). Crisis windows often push GARCH near IGARCH territory; refit on subsamples to sanity check.
4. **Conflating volatility and variance.** `res.conditional_volatility` is sigma_t (already square-rooted); `res.forecast().variance` is variance, not sigma. Squaring or sqrt-ing the wrong one is a common silent bug that produces vol estimates 100x too large or small.
5. **Mean model misspecification leaking into volatility.** If returns have meaningful autocorrelation (intraday, illiquid assets), `mean='Constant'` dumps that structure into the residuals and biases volatility estimates. Use `mean='ARX'` with appropriate lags (verify with PACF), or pre-filter returns with an ARMA model.
6. **Not setting `reindex=False`.** Default `reindex=True` aligns forecasts to the *original* index with NaNs in non-forecast rows, which is rarely what you want for downstream code. `reindex=False` returns a clean DataFrame indexed by forecast origin.
7. **Out-of-sample forecast leakage in walk-forward.** Refitting the GARCH every day on an expanding window without time-discipline produces look-ahead-free forecasts but is expensive. A common shortcut — fitting once and using `res.forecast(start=date_t, horizon=1)` for each `t` — assumes parameters are constant; check stability via rolling-window refits before trusting.

## Diagnostic Plots

Two checks worth running by default after any GARCH fit:

```python
import matplotlib.pyplot as plt
import scipy.stats as ss

# 1. Conditional volatility overlay.
fig, ax = plt.subplots(figsize=(10, 4))
ax.plot(log_ret_pct.abs(), color='C0', alpha=0.3, label='|returns|')
ax.plot(res.conditional_volatility, color='C3', label='GARCH sigma_t')
ax.set_title('Realized vs conditional volatility')
ax.legend()

# 2. Standardized-residual QQ plot — checks innovation distribution.
fig, ax = plt.subplots(figsize=(5, 5))
nu = res.params.get('nu', None)
if nu is not None:
    ss.probplot(res.std_resid.dropna(), dist=ss.t, sparams=(nu,), plot=ax)
    ax.set_title(f'Student-t (nu={nu:.2f}) QQ plot of std. resid.')
else:
    ss.probplot(res.std_resid.dropna(), dist=ss.norm, plot=ax)
    ax.set_title('Normal QQ plot of std. resid.')
```

A clean GARCH fit shows: (1) conditional vol that tracks realized abs-return clusters without lagging too much, and (2) a near-linear QQ plot on the chosen innovation distribution.

## References

### Primary library
- [bashtage/arch on GitHub](https://github.com/bashtage/arch) — upstream repo, issues, and releases (Kevin Sheppard, University of Oxford)
- [arch documentation (stable)](https://arch.readthedocs.io/en/stable/) — pinned to v7.x for the snippets above
- [arch examples directory](https://github.com/bashtage/arch/tree/main/examples) — Jupyter notebooks for GARCH/EGARCH/HAR/bootstrap

### Deep-dive docs (specific pages worth bookmarking)
- [`arch.univariate.arch_model` API](https://arch.readthedocs.io/en/latest/univariate/generated/arch.univariate.arch_model.html) — the canonical builder; all `mean`/`vol`/`dist` combinations enumerated
- [Univariate volatility introduction](https://arch.readthedocs.io/en/latest/univariate/introduction.html) — mean+volatility composition, what each spec means
- [Volatility forecasting page](https://arch.readthedocs.io/en/latest/univariate/forecasting.html) — analytic vs simulation vs bootstrap forecast methods, multi-step semantics
- [Distributions module](https://arch.readthedocs.io/en/latest/univariate/distribution.html) — Normal / Student-t / SkewStudent / GED; what `dist='t'` vs `'skewt'` actually fit
- [`ConvergenceMonitor` / fit diagnostics](https://arch.readthedocs.io/en/latest/univariate/results.html) — how to read the `ARCHModelResult`
- [Bootstrap module overview](https://arch.readthedocs.io/en/latest/bootstrap/index.html) — `StationaryBootstrap` for serially-dependent series, paired with GARCH residual checks

### Adjacent / alternative libraries
- [statsmodels `tsa.regime_switching`](https://www.statsmodels.org/stable/tsa.html#markov-regime-switching) — Markov-switching ARCH/GARCH when a single regime fails (also see `markov-regime-detection`)
- [pyflux](https://github.com/RJT1990/pyflux) — Bayesian GARCH / GAS models; dormant but the only easy GAS implementation in Python
- [mfe-toolbox (Sheppard)](https://www.kevinsheppard.com/code/matlab/mfe-toolbox/) — MATLAB ancestor of `arch`; has multivariate (DCC/BEKK) and realized-volatility families not yet in `arch`
- [pyextremes](https://github.com/georgebv/pyextremes) — extreme-value theory next to GARCH-implied tail risk
- [`PyMC` for stochastic volatility](https://www.pymc.io/projects/examples/en/latest/case_studies/stochastic_volatility.html) — when SV (latent log-vol) is the right model rather than GARCH

### Academic papers
- Engle, R. F. (1982). "Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation." *Econometrica* 50(4), 987-1008. [Econometric Society](https://www.econometricsociety.org/publications/econometrica/1982/07/01/autoregressive-conditional-heteroscedasticity-estimates) — the original ARCH paper.
- Bollerslev, T. (1986). "Generalized Autoregressive Conditional Heteroskedasticity." *Journal of Econometrics* 31(3), 307-327. [DOI: 10.1016/0304-4076(86)90063-1](https://doi.org/10.1016/0304-4076(86)90063-1) — GARCH(p,q) generalization.
- Nelson, D. B. (1991). "Conditional Heteroskedasticity in Asset Returns: A New Approach." *Econometrica* 59(2), 347-370. [JSTOR 2938260](https://www.jstor.org/stable/2938260) — EGARCH; log-variance, no positivity constraints, leverage.
- Glosten, L. R., Jagannathan, R., & Runkle, D. E. (1993). "On the Relation between the Expected Value and the Volatility of the Nominal Excess Return on Stocks." *Journal of Finance* 48(5), 1779-1801. [DOI: 10.1111/j.1540-6261.1993.tb05128.x](https://doi.org/10.1111/j.1540-6261.1993.tb05128.x) — GJR-GARCH, leverage effect for equities.
- Hansen, P. R., Lunde, A., & Nason, J. M. (2011). "The Model Confidence Set." *Econometrica* 79(2), 453-497. [DOI: 10.3982/ECTA5771](https://doi.org/10.3982/ECTA5771) — implemented as `arch.bootstrap.MCS`; the right way to compare GARCH variants on out-of-sample loss.
- Sheppard, K. (2024). *arch: GARCH and other Financial Econometrics Toolbox*. v7.x — the package itself; see the README for citation guidance.

### Tutorials & write-ups
- [Kevin Sheppard, MFE Toolbox notes](https://www.kevinsheppard.com/teaching/python/notes/) — Oxford lecture notes for the same author who wrote `arch`; the closest you get to a long-form tutorial
- [arch GARCH examples notebook](https://nbviewer.org/github/bashtage/arch/blob/main/examples/univariate_volatility_modeling.ipynb) — Sheppard's own walkthrough of GARCH/EGARCH/APARCH on S&P 500 returns
- [Diebold-Mariano tutorial](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-examples.html) — testing whether one GARCH variant beats another on out-of-sample forecast loss

### Last cross-checked
2026-05-20 — via Context7 `/bashtage/arch` (508 snippets, High reputation) + WebSearch verification of all paper DOIs/URLs.
