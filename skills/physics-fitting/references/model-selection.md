# Model comparison — AIC and BIC

Reduced chi-squared always improves as you add parameters, so it cannot tell you
whether the extra complexity is justified. Information criteria penalize
parameter count and let you compare non-nested models on the same data.

- **AIC** = 2k - 2 ln(L) — Akaike Information Criterion. Estimates predictive
  loss; tends to prefer slightly richer models.
- **BIC** = k ln(n) - 2 ln(L) — Bayesian Information Criterion. Penalizes
  parameters more heavily as sample size grows; prefers simpler models.

where `k` = number of free parameters, `n` = number of data points, and `L` is
the maximized likelihood. **Lower is better, and only differences matter.** Rules
of thumb for ΔAIC (or ΔBIC) relative to the best model:

| Δ (worse − best) | Evidence against the worse model |
|---|---|
| 0 – 2 | negligible; models are effectively tied |
| 4 – 7 | considerably less support |
| > 10 | decisive; the worse model is essentially ruled out |

## Log-likelihood for Gaussian errors

With independent Gaussian uncertainties `sigma_i`, the maximized log-likelihood
reduces to a chi-squared plus constants:

```
ln L = -0.5 * chi2  -  0.5 * n * ln(2*pi)  -  sum_i ln(sigma_i)
```

The `sigma`-dependent constant term is the same for every model fit to the same
data, so it cancels in AIC/BIC *differences*. Keep it if you want absolute
values; drop it if you only rank models.

## Comparison table

```python
import numpy as np
from scipy.optimize import curve_fit

def compare_models(models, x, y, sigma):
    """models: list of (name, func, p0). Returns rows sorted by AIC."""
    n    = len(y)
    rows = []
    for name, func, p0 in models:
        try:
            popt, _ = curve_fit(func, x, y, p0=p0,
                                sigma=sigma, absolute_sigma=True)
            k     = len(popt)
            chi2  = np.sum(((y - func(x, *popt)) / sigma) ** 2)
            lnL   = -0.5 * chi2 - 0.5 * n * np.log(2 * np.pi) - np.sum(np.log(sigma))
            aic   = 2 * k - 2 * lnL
            bic   = k * np.log(n) - 2 * lnL
            rows.append((name, k, chi2 / (n - k), aic, bic))
        except RuntimeError:
            rows.append((name, np.nan, np.inf, np.inf, np.inf))

    rows.sort(key=lambda r: r[3])                 # by AIC
    best_aic = rows[0][3]
    print(f"{'model':<16}{'k':>3}{'chi2/ndof':>12}{'AIC':>10}{'dAIC':>9}")
    for name, k, redchi, aic, bic in rows:
        print(f"{name:<16}{k:>3}{redchi:>12.3f}{aic:>10.2f}{aic - best_aic:>9.2f}")
    return rows

def power_law(t, A, m, C):
    return A * t ** (-m) + C

def exponential_decay(t, A, tau, C):
    return A * np.exp(-t / tau) + C

compare_models(
    [("exponential", exponential_decay, [10, 3, 0.1]),
     ("power_law",   power_law,        [10, 1, 0.1])],
    x=t, y=y, sigma=sig)
```

## Notes and caveats

- **lmfit gives these for free.** After a fit, `result.aic` and `result.bic` are
  already computed (from the residual sum, using an equivalent likelihood). Use
  them to avoid recomputing.
- **Same data, same weighting.** AIC/BIC comparisons are only valid when every
  model is fit to the identical dataset with the identical uncertainties. Do not
  compare across different `sigma` conventions or subsets.
- **AIC vs BIC.** Prefer AIC when the goal is prediction and you doubt the "true"
  model is in your set; prefer BIC when you want the most parsimonious model and
  `n` is large. Report both; if they disagree, say so.
- **Not a substitute for goodness-of-fit.** The best model by AIC can still be a
  bad fit. Always check reduced chi-squared and residuals (see
  [diagnostics-and-pitfalls.md](diagnostics-and-pitfalls.md)) on the winner.
- **AICc for small samples.** When `n/k` is small (< ~40), use the corrected
  AICc = AIC + 2k(k+1)/(n-k-1) instead of AIC.
