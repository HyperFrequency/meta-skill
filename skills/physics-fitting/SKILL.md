---
name: physics-fitting
version: 0.1.0
description: >-
  Nonlinear least-squares and chi-squared curve fitting for physics and
  experimental data, with correct error propagation, parameter covariance,
  confidence intervals, residual diagnostics, goodness-of-fit (reduced
  chi-squared), and model comparison (AIC/BIC) via scipy and lmfit. Use when
  extracting physical parameters or constants from measured or simulated data,
  propagating measurement uncertainties into derived quantities, or deciding
  which of several candidate models best fits data with proper error bars. Do
  NOT use when you need full posterior distributions or MCMC sampling (use
  `bayesian-inference` or `pymc`), when the functional form itself is unknown
  and must be discovered from data, or when you must first integrate a
  differential equation before fitting its trajectory (use `ode-solver`, then
  fit the output with this skill).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "scipy, numpy, lmfit: BSD-3-Clause; matplotlib: Matplotlib License (PSF-based)"
---

# Physics Data Fitting

## Overview

Extract physical parameters from measured or simulated data by minimizing a
weighted residual (chi-squared) between a model function and the data, then
report each parameter with a defensible uncertainty. This skill covers the full
loop a careful analysis needs: weighted nonlinear least squares, parameter
covariance and confidence intervals, propagation of those uncertainties into
derived quantities, goodness-of-fit assessment, and principled model comparison.

Two libraries do the work. Use **scipy** (`scipy.optimize.curve_fit`) for quick
unconstrained fits, and **lmfit** when you need parameter bounds, fixed
parameters, algebraic constraints between parameters, composite models, or
profile-likelihood confidence intervals. Everything here assumes you have real
measurement uncertainties and want error bars you can trust.

## When to Use This Skill

- Fitting a known model function to experimental data to extract parameters.
- Measuring a physical constant, rate, lifetime, resonance frequency, etc.
- Deciding which of several competing models best explains the data.
- Propagating measurement uncertainties into a quantity derived from the fit
  (e.g. half-life from a decay constant, a ratio, an integral).
- Any parameter estimation where the deliverable is a value **and** its error
  bar, plus evidence that the fit is actually good.

## When NOT to Use This Skill

- **You need the full posterior or MCMC samples** (multimodal likelihood, strong
  priors, marginal distributions) — use `bayesian-inference` or `pymc`.
- **The functional form is unknown** and must be discovered from the data rather
  than assumed — this skill fits a model you already have.
- **The data is a trajectory of a differential equation** you have not yet
  integrated — integrate with `ode-solver` first, then fit its output here.
- **You only need a straight-line / ordinary least squares regression** with
  standard diagnostics — `statistical-analysis` / `statsmodels` are more direct.
- **You need unit / dimensional bookkeeping** on the parameters — pair with
  `dimensional-analysis`.

## Choosing a tool

| Situation | Use |
|---|---|
| Fast unconstrained fit, Gaussian errors, good initial guess | `scipy.optimize.curve_fit` |
| Parameter bounds, fixed params, `expr` constraints, shared params | `lmfit.Model` |
| Asymmetric / profile-likelihood confidence intervals | `lmfit` `conf_interval()` |
| Composite / built-in models (Gaussian + linear background, etc.) | `lmfit` built-in models |
| Robust fit against outliers | `scipy` `loss='soft_l1'` or `lmfit` `method='least_squares'` with robust loss |

## Quick start: weighted nonlinear least squares (scipy)

The single most important habit: pass real uncertainties via `sigma` and set
`absolute_sigma=True`, or your reported errors will be silently rescaled.

```python
import numpy as np
from scipy.optimize import curve_fit

def exponential_decay(t, A, tau, C):      # y = A*exp(-t/tau) + C
    return A * np.exp(-t / tau) + C

t = np.array([0.5, 1, 2, 3, 5, 7, 10, 15, 20])
y = np.array([9.8, 8.1, 5.5, 3.9, 2.1, 1.3, 0.7, 0.35, 0.22])
sig = np.array([0.3, 0.2, 0.2, 0.15, 0.1, 0.1, 0.08, 0.05, 0.04])

popt, pcov = curve_fit(exponential_decay, t, y,
                       p0=[10, 3, 0.1],          # initial guess matters
                       sigma=sig, absolute_sigma=True)

perr = np.sqrt(np.diag(pcov))                    # 1-sigma parameter errors
chi2 = np.sum(((y - exponential_decay(t, *popt)) / sig) ** 2)
chi2_red = chi2 / (len(t) - len(popt))           # reduced chi-squared, want ~1
```

Full treatment — bounds, robust loss, covariance-sampled confidence bands, and
the data/best-fit/residual plot — is in
[references/scipy-fitting.md](references/scipy-fitting.md).

## Bounded fits and confidence intervals (lmfit)

`lmfit` wraps the same optimizers but lets you name parameters, bound them, fix
them, tie them together with `expr`, and get a formatted report plus
profile-likelihood confidence intervals (which can be asymmetric — the honest
answer when the likelihood is not parabolic).

```python
from lmfit import Model
model = Model(exponential_decay)
params = model.make_params(A=10, tau=3, C=0)
params['tau'].min = 0.01          # physical: lifetime must be positive
result = model.fit(y, params, t=t, weights=1.0 / sig)
print(result.fit_report())        # values, stderr, correlations, redchi, AIC/BIC
ci = result.conf_interval()       # asymmetric intervals via profile likelihood
```

Built-in models, composite models, `expr` constraints, and residual plotting are
in [references/lmfit-workflow.md](references/lmfit-workflow.md).

## Model comparison (AIC / BIC)

Reduced chi-squared alone rewards adding parameters. To choose between models of
different complexity, compare information criteria — lower is better, and only
**differences** are meaningful (ΔAIC > ~10 is decisive). `lmfit` exposes
`result.aic` and `result.bic` directly; the explicit Gaussian-likelihood
computation and a side-by-side comparison table are in
[references/model-selection.md](references/model-selection.md).

## Error propagation to derived quantities

A parameter's uncertainty rarely stays put — you usually want the error on
something computed from the fit. Propagate the full covariance matrix through the
derived function with the Jacobian: sigma_f^2 = J Σ J^T. This correctly accounts
for parameter correlations, which naive add-in-quadrature does not.

```python
half_life = popt[1] * np.log(2)              # tau -> t_1/2
d_half   = perr[1] * np.log(2)               # only valid because it's linear in tau
```

For nonlinear derived quantities or several correlated parameters, use the
Jacobian method (or the `uncertainties` package) as shown in
[references/error-propagation.md](references/error-propagation.md).

## Assessing the fit

Never trust parameters from a fit you have not checked. Read reduced
chi-squared, look at the residuals, and watch for the common traps (default
`absolute_sigma=False`, bad initial guess landing in a wrong minimum, strongly
correlated parameters, structure in the residuals). The interpretation table and
the full pitfalls checklist are in
[references/diagnostics-and-pitfalls.md](references/diagnostics-and-pitfalls.md).

## References

- [references/scipy-fitting.md](references/scipy-fitting.md) — `curve_fit` in
  full: bounds, robust loss, confidence bands, residual plots.
- [references/lmfit-workflow.md](references/lmfit-workflow.md) — parameters,
  constraints, built-in/composite models, profile-likelihood CIs.
- [references/model-selection.md](references/model-selection.md) — AIC/BIC,
  log-likelihood, comparison table, when each criterion applies.
- [references/error-propagation.md](references/error-propagation.md) — Jacobian
  propagation, correlations, worked examples, the `uncertainties` package.
- [references/diagnostics-and-pitfalls.md](references/diagnostics-and-pitfalls.md)
  — goodness-of-fit interpretation, residual diagnostics, pitfalls checklist.

## Related skills

- `bayesian-inference`, `pymc` — full posteriors / MCMC when least squares is not enough.
- `ode-solver` — integrate a differential equation, then fit its output here.
- `statistical-analysis`, `statsmodels` — linear/OLS regression and general stats.
- `dimensional-analysis` — keep units and dimensions on parameters straight.
- `matplotlib` — publication-quality fit and residual figures.
