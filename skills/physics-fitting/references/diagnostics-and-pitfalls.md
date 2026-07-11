# Goodness-of-fit, residual diagnostics, and pitfalls

A fit is not done when the optimizer converges — it is done when you have
checked that the model actually describes the data and the reported errors mean
what they claim.

## Reduced chi-squared

Reduced chi-squared is chi-squared divided by the degrees of freedom
(`ndof = n_points - n_free_params`). With correct Gaussian error bars it should
be about 1.

| chi2/ndof | Interpretation |
|---|---|
| ≈ 1 | Good fit — model matches data within the stated uncertainties. |
| ≪ 1 | Errors overestimated, or model is over-parameterized (overfitting). |
| ≫ 1 | Poor fit — model inadequate, or uncertainties underestimated. |
| ~0.5 – 2 | Usually acceptable in practice; judge with the residual plot. |

Do not read chi2/ndof in isolation: a value near 1 with structured residuals is
still a bad fit, and a value above 1 can simply mean your error bars are a bit
small. For a formal test, compare chi-squared against the chi-squared
distribution with `ndof` degrees of freedom (`scipy.stats.chi2.sf(chi2, ndof)`
gives the p-value — small p means reject the model).

## Residual diagnostics

Normalized residuals `(y - model)/sigma` should look like standard-normal noise
scattered around zero with no pattern.

- **Trend / curvature** in residuals vs x → the model is missing a term (wrong
  functional form). No amount of refitting fixes structure.
- **Fanning** (residuals grow with x or with y) → your error model is wrong; the
  uncertainties are not constant in the way you assumed.
- **Runs** (long stretches on one side of zero) → correlated residuals; check the
  runs test or `statsmodels` Durbin-Watson.
- **Non-Gaussian spread** → histogram the normalized residuals; heavy tails
  suggest outliers (switch to robust loss) and skew suggests a wrong model.
- **A single huge residual** → an outlier is dominating chi-squared. Investigate
  the point before deleting it; use robust loss if it is real but non-Gaussian.

```python
import numpy as np
r = (y - model(x, *popt)) / sigma
print("mean:", r.mean(), " std:", r.std())         # want ~0 and ~1
# normality of residuals:
from scipy.stats import shapiro
print("Shapiro-Wilk p:", shapiro(r).pvalue)         # small p => not Gaussian
```

## Pitfalls checklist

| Pitfall | Fix |
|---|---|
| `absolute_sigma=False` (the scipy default) with real error bars | Set `absolute_sigma=True` or your parameter errors are silently rescaled. |
| Bad initial guess lands in a wrong local minimum | Try several `p0`, use physically motivated guesses, or use lmfit bounds; rescale so parameters are O(1). |
| Strongly correlated parameters | Inspect off-diagonal `pcov`; reparameterize, fix one, or add data that breaks the degeneracy. |
| Non-Gaussian / outlier-laden residuals | Histogram residuals; use robust loss (`soft_l1`, `huber`) or investigate the outliers. |
| Too many parameters (overfitting) | Compare with AIC/BIC (see [model-selection.md](model-selection.md)); watch for chi2/ndof ≪ 1. |
| Reporting only statistical errors | State systematic uncertainties separately; do not fold them into the fit error. |
| Extrapolating beyond the data range | Confidence bands widen fast outside the fitted domain; do not trust the model there. |
| Fitting integrated / cumulative data | Correlated points violate the independent-errors assumption; fit the differential form or use the full covariance. |
| Ignoring parameter bounds hit during the fit | If a parameter sits on its bound, its error bar is meaningless; loosen the bound or reconsider the model. |
| Units / dimension mismatch in the model | Keep units explicit; pair with `dimensional-analysis`. |

## Sanity checks before you report

1. chi2/ndof is near 1 **and** residuals show no structure.
2. Every parameter has a finite, physically sensible error bar.
3. Covariance off-diagonals are not near ±1 (no runaway correlation).
4. The fit is stable to a modest change in `p0`.
5. Derived quantities are propagated with correlations
   (see [error-propagation.md](error-propagation.md)), not add-in-quadrature.
