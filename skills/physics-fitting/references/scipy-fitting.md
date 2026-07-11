# scipy.optimize.curve_fit — full workflow

`curve_fit` is the fastest path to a weighted nonlinear least-squares fit. It
minimizes the sum of squared, weighted residuals and returns the best-fit
parameters and their covariance matrix.

## Signature essentials

```python
popt, pcov = curve_fit(
    f, xdata, ydata,
    p0=None,               # initial guess; provide it for anything nonlinear
    sigma=None,            # per-point uncertainties (1-sigma)
    absolute_sigma=False,  # SET True when sigma are real error bars
    bounds=(-inf, inf),    # (lower, upper) arrays -> constrained fit
    method=None,           # 'lm' (default, unbounded), 'trf', 'dogbox'
    maxfev=...,            # raise if it fails to converge
)
```

- `f(x, *params)` — the model. First arg is the independent variable, the rest
  are the parameters to fit, in order.
- `popt` — best-fit parameter values (a 1-D array).
- `pcov` — parameter covariance matrix. `np.sqrt(np.diag(pcov))` gives the
  1-sigma standard errors; off-diagonal entries encode correlations.

### absolute_sigma — the setting people get wrong

- `absolute_sigma=True`: `sigma` is taken as true measurement error. `pcov` is
  the real covariance and the parameter errors are absolute. **Use this whenever
  your `sigma` are physical error bars.**
- `absolute_sigma=False` (default): only the *relative* weights matter; `pcov` is
  rescaled by the reduced chi-squared so that it comes out ~1. This hides a bad
  fit and rescales your error bars. Only appropriate when you do not know the
  absolute error scale.

## Worked example with diagnostics

```python
import numpy as np
from scipy.optimize import curve_fit

def exponential_decay(t, A, tau, C):
    return A * np.exp(-t / tau) + C

t   = np.array([0.5, 1, 2, 3, 5, 7, 10, 15, 20])
y   = np.array([9.8, 8.1, 5.5, 3.9, 2.1, 1.3, 0.7, 0.35, 0.22])
sig = np.array([0.3, 0.2, 0.2, 0.15, 0.1, 0.1, 0.08, 0.05, 0.04])

popt, pcov = curve_fit(exponential_decay, t, y,
                       p0=[10, 3, 0.1],
                       sigma=sig, absolute_sigma=True)

perr = np.sqrt(np.diag(pcov))
for name, val, err in zip("A tau C".split(), popt, perr):
    print(f"{name:>3} = {val:.3f} +/- {err:.3f}")

resid_norm = (y - exponential_decay(t, *popt)) / sig      # residuals in sigma
chi2      = np.sum(resid_norm ** 2)
ndof      = len(t) - len(popt)
print(f"chi2/ndof = {chi2:.2f}/{ndof} = {chi2 / ndof:.2f}")
```

## Bounds and physical constraints

Use `bounds` to keep parameters physical (a lifetime cannot be negative). Bounds
force `method='trf'`, which is also more robust for hard problems.

```python
popt, pcov = curve_fit(
    exponential_decay, t, y, p0=[10, 3, 0.1],
    sigma=sig, absolute_sigma=True,
    bounds=([0, 0.01, -1], [np.inf, np.inf, 1]),   # A>=0, tau>0, C in [-1,1]
)
```

## Robust fitting against outliers

Least squares is sensitive to outliers. `curve_fit` delegates to
`scipy.optimize.least_squares`, so with `method='trf'` or `'dogbox'` you can pass
a robust loss:

```python
popt, pcov = curve_fit(exponential_decay, t, y, p0=[10, 3, 0.1],
                       method='trf', loss='soft_l1', f_scale=1.0)
```

`loss` options: `'linear'` (default), `'soft_l1'`, `'huber'`, `'cauchy'`,
`'arctan'`. `f_scale` sets the residual value above which points are
down-weighted. Robust loss changes the meaning of `pcov`; treat the resulting
errors with care and cross-check against a bootstrap.

## Confidence band by covariance sampling

Draw parameter sets from the multivariate normal implied by `popt`/`pcov`,
evaluate the model for each, and take percentiles. This propagates the full
covariance (including correlations) into the curve.

```python
import numpy as np
rng     = np.random.default_rng(42)
t_fine  = np.linspace(t.min(), t.max(), 300)
samples = rng.multivariate_normal(popt, pcov, size=2000)
curves  = np.array([exponential_decay(t_fine, *p) for p in samples])
lo, hi  = np.percentile(curves, [2.5, 97.5], axis=0)     # 95% band
```

## Data + best-fit + residual figure

```python
import matplotlib.pyplot as plt
fig, (ax_fit, ax_res) = plt.subplots(
    2, 1, figsize=(8, 7), sharex=True,
    gridspec_kw={'height_ratios': [3, 1]})

ax_fit.errorbar(t, y, yerr=sig, fmt='ko', capsize=3, label='data')
ax_fit.plot(t_fine, exponential_decay(t_fine, *popt), 'r-', lw=2, label='fit')
ax_fit.fill_between(t_fine, lo, hi, color='r', alpha=0.2, label='95% CI')
ax_fit.set_ylabel('y'); ax_fit.legend()

ax_res.errorbar(t, resid_norm, yerr=1, fmt='ko', capsize=3)
ax_res.axhline(0, color='r', ls='--')
ax_res.set_ylabel('resid (sigma)'); ax_res.set_xlabel('t')
fig.tight_layout()
fig.savefig('fit_with_residuals.png', dpi=150, bbox_inches='tight')
```

## Failure modes

- **`RuntimeError: Optimal parameters not found`** — bad `p0`, too few
  iterations, or a model that cannot fit. Improve the guess, raise `maxfev`, or
  rescale the data so parameters are O(1).
- **`OptimizeWarning: Covariance of the parameters could not be estimated`** —
  the fit is degenerate (a flat direction or too few points). Fix or remove a
  parameter, or add data.
- **Huge parameter errors with a good-looking curve** — strongly correlated
  parameters. Inspect `pcov` off-diagonals; reparameterize or fix one.
