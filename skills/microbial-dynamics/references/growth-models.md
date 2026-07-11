# Growth Curve Models

Fit bacterial growth (OD600 or ln-biomass) time-series to standard primary
models and recover interpretable parameters: initial density `y0`, carrying
capacity `K`, maximum specific growth rate `mu_max` (h^-1), and lag duration
`lag` (h). All fitting uses `scipy.optimize.curve_fit` (Levenberg-Marquardt /
trust-region), which returns the covariance matrix so you get per-parameter
standard errors.

## Model equations

```python
import numpy as np

def logistic(t, y0, K, r, lag):
    """Logistic (Verhulst) growth. r is the intrinsic rate; symmetric sigmoid."""
    return K / (1 + ((K - y0) / y0) * np.exp(-r * (t - lag)))

def gompertz(t, y0, K, mu_max, lag):
    """Modified Gompertz (Zwietering parameterization). Asymmetric sigmoid;
    mu_max and lag map directly to biological quantities."""
    return y0 + (K - y0) * np.exp(-np.exp((mu_max * np.e / (K - y0)) * (lag - t) + 1))

def baranyi(t, y0, K, mu_max, lag):
    """Baranyi-Roberts model (log-scale). Most mechanistically justified;
    models the physiological adjustment during lag explicitly. Fit on ln(OD)."""
    A_t = t + (1 / mu_max) * np.log(
        np.exp(-mu_max * t) + np.exp(-mu_max * lag) - np.exp(-mu_max * (t + lag)))
    return K - np.log(1 + (np.exp(K) - np.exp(y0)) / np.exp(y0) * np.exp(-mu_max * A_t))
```

Notes:
- Logistic uses `r` (intrinsic rate), not `mu_max` directly; for a symmetric
  logistic the inflection slope relates to `r*K/4`. Gompertz and Baranyi are
  parameterized so the fitted parameter *is* `mu_max`.
- Baranyi is written on the natural-log scale — pass `y0`, `K` as `ln(OD)`
  values (or fit `np.log(od600)` and exponentiate for plotting).

## Reusable fitting helper

```python
from scipy.optimize import curve_fit

def fit_growth_curve(time, od600, model='logistic'):
    """Fit a growth model; return (result_dict, popt).

    result_dict has {param: {'value', 'std'}} plus 'r_squared' and 'model'.
    """
    models = {'logistic': logistic, 'gompertz': gompertz, 'baranyi': baranyi}
    func = models[model]

    # Data-driven initial guesses
    y0_guess  = od600[0]
    K_guess   = od600.max()
    r_guess   = 0.5
    lag_guess = max(time[np.argmax(np.gradient(od600))] - 1, 0)

    p0 = [y0_guess, K_guess, r_guess, lag_guess]
    bounds = ([0, 0, 0, 0], [np.inf, np.inf, 10, time.max()])
    popt, pcov = curve_fit(func, time, od600, p0=p0, bounds=bounds, maxfev=10000)
    perr = np.sqrt(np.diag(pcov))

    residuals = od600 - func(time, *popt)
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((od600 - np.mean(od600)) ** 2)
    r_squared = 1 - ss_res / ss_tot

    names = ['y0', 'K', 'mu_max', 'lag']
    result = {n: {'value': v, 'std': e} for n, v, e in zip(names, popt, perr)}
    result['r_squared'] = r_squared
    result['model'] = model
    return result, popt
```

`curve_fit` parameters worth knowing:
- `p0` — initial guess; the single biggest determinant of convergence. Seed it
  from the data as above.
- `bounds` — keeps parameters physical (non-negative, `lag <= t_max`). Bounded
  fits use the `trf` method automatically.
- `maxfev` / `max_nfev` — raise if you see `RuntimeError: Optimal parameters not
  found`.
- `sigma` — pass per-point measurement errors for weighted least squares.

## Model selection

Compare candidate models by information criterion, not R-squared (which never
decreases as you add parameters). For least-squares fits with `n` points and
`k` parameters:

```python
def aic_bic(residuals, k):
    n = len(residuals)
    rss = np.sum(residuals ** 2)
    aic = n * np.log(rss / n) + 2 * k
    bic = n * np.log(rss / n) + k * np.log(n)
    return aic, bic
```

Guidance:
- **Logistic** — fewest assumptions, symmetric; good default when data is sparse.
- **Gompertz** — asymmetric, usually fits bacterial curves better; `mu_max` and
  `lag` are directly interpretable.
- **Baranyi** — most mechanistic and generally the reference for predictive
  microbiology, but needs enough points *during the lag/early-exponential
  phase* to identify the lag term. With coarse sampling it overfits.
- Lower AIC/BIC wins; a difference >2 is meaningful, >10 is decisive.

## Multi-condition workflow

```python
import pandas as pd

data = pd.read_csv('growth_data.csv')   # columns: time, condition, od600
rows = []
for condition, group in data.groupby('condition'):
    fit, _ = fit_growth_curve(group['time'].values, group['od600'].values,
                              model='gompertz')
    rows.append({'condition': condition,
                 'mu_max': fit['mu_max']['value'],
                 'lag':    fit['lag']['value'],
                 'K':      fit['K']['value'],
                 'r2':     fit['r_squared']})
print(pd.DataFrame(rows))
```

For statistical comparison of `mu_max` across conditions (t-tests, ANOVA, mixed
models on replicate-level parameter estimates), hand the per-replicate fits to
`statistical-analysis`.

## Troubleshooting

- **Fit fails to converge** — improve `p0` (seed from data), widen `maxfev`,
  confirm the series actually reaches stationary phase, and check for negative
  OD values from over-subtracted blanks.
- **Nonsensical `lag` (negative or > t_max)** — tighten `bounds`; sample more
  densely early.
- **Baranyi returns NaN** — you passed linear OD where ln(OD) is expected, or
  `mu_max` guess was ~0 (division blows up). Fit `np.log(od)` and guess
  `mu_max ~ 0.3-0.8`.

## Reference

- Baranyi & Roberts (1994), *Int. J. Food Microbiol.* 23:277-294,
  doi:10.1016/0168-1605(94)90157-0.
- Zwietering et al. (1990), *Appl. Environ. Microbiol.* 56:1875-1881 (modified
  Gompertz parameterization).
- `scipy.optimize.curve_fit` documentation.
