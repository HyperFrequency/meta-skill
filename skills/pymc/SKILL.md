---
name: pymc
version: 0.1.0
description: Bayesian modeling and probabilistic programming with PyMC 5.x. Build hierarchical/regression models, sample with NUTS/MCMC, run variational inference (ADVI), do prior/posterior predictive checks, diagnose convergence (R-hat, ESS, divergences), and compare models with LOO/WAIC via ArviZ. Use when fitting Bayesian models or quantifying uncertainty. Not for frequentist regression (use statsmodels/scikit-learn), plain MLE fitting, or deep-learning probabilistic models (use a dedicated PPL/torch). For Bayesian time-series forecasting see timesfm-forecasting; for general stats see statsmodels.
license: Apache License, Version 2.0
metadata:
    skill-author: K-Dense Inc.
---

# PyMC Bayesian Modeling

## Overview

PyMC (5.x+) is a Python library for Bayesian modeling and probabilistic programming. It pairs with ArviZ for diagnostics and visualization. This skill is a router: the inline content below is a quick reference; the bundled `references/`, `scripts/`, and `assets/` hold the deep material — read those when you need detail.

## When to Use This Skill

- Building Bayesian models (regression, hierarchical/multilevel, GLMs, time series)
- MCMC sampling (NUTS) or variational inference (ADVI)
- Prior/posterior predictive checks and uncertainty quantification
- Diagnosing sampling issues (divergences, R-hat, ESS)
- Comparing models with LOO/WAIC; handling missing data or measurement error

## When NOT to Use

- Frequentist/point-estimate regression → `statsmodels` or `scikit-learn`
- Plain maximum-likelihood fitting with no priors/posterior
- Deep probabilistic / neural models at scale → a torch-based PPL
- Pure forecasting without a custom generative model → `timesfm-forecasting`

## Core Workflow (at a glance)

1. **Prepare data** — standardize continuous predictors; define `coords` for named dims.
2. **Build model** — weakly informative priors; `HalfNormal`/`Exponential` for scales; `dims` over `shape`.
3. **Prior predictive check** — `pm.sample_prior_predictive()`; confirm priors imply plausible data.
4. **Fit** — `pm.sample(draws=2000, tune=1000, chains=4, target_accept=0.9, idata_kwargs={'log_likelihood': True})`.
5. **Diagnostics** — `check_diagnostics()` in `scripts/model_diagnostics.py`; require R-hat < 1.01, ESS > 400, 0 divergences.
6. **Posterior predictive check** — `pm.sample_posterior_predictive(...)`; `az.plot_ppc`.
7. **Analyze** — `az.summary`, `az.plot_forest`, `az.plot_posterior`; report HDIs, not just points.
8. **Predict** — `pm.set_data(...)` then `pm.sample_posterior_predictive`.

Full runnable templates and per-step detail: **`references/workflows.md`**.

### Minimal model

```python
import pymc as pm
import arviz as az

with pm.Model(coords={'predictors': cols}) as model:
    alpha = pm.Normal('alpha', mu=0, sigma=1)
    beta = pm.Normal('beta', mu=0, sigma=1, dims='predictors')
    sigma = pm.HalfNormal('sigma', sigma=1)
    mu = alpha + pm.math.dot(X_scaled, beta)
    y = pm.Normal('y', mu=mu, sigma=sigma, observed=y_obs)
    idata = pm.sample(draws=2000, tune=1000, chains=4, target_accept=0.9,
                      idata_kwargs={'log_likelihood': True})
```

## Model Patterns

Linear, logistic, hierarchical (non-centered), Poisson/NegativeBinomial, AR time series, and mixture models — with full code — are in **`references/workflows.md`** ("Model Building Patterns"). Always use **non-centered parameterization** for hierarchical models to avoid divergences. Ready-to-run starting points:

- `assets/linear_regression_template.py` — Bayesian linear regression, full workflow.
- `assets/hierarchical_model_template.py` — multilevel model, non-centered, group-level analysis.

## Choosing Distributions

Pick priors and likelihoods from **`references/distributions.md`** (continuous, discrete, multivariate, mixture, time series, with selection guidance). Defaults: `HalfNormal`/`Exponential` for scales, `Normal`/`StudentT` for unbounded, `Beta` for probabilities, `Normal`→continuous / `Bernoulli`→binary / `Poisson`→counts / `NegativeBinomial`→overdispersed counts likelihoods.

## Sampling and Inference

NUTS is the default. For VI (ADVI/full-rank/SVGD), MAP, SMC, predictive sampling, reparameterization tricks, and method selection, see **`references/sampling_inference.md`**.

```python
idata = pm.sample(draws=2000, tune=1000, chains=4, target_accept=0.9)
approx = pm.fit(n=20000, method='advi')  # fast approximation / initialization
```

## Diagnostics and Model Comparison

```python
from scripts.model_diagnostics import check_diagnostics, create_diagnostic_report
from scripts.model_comparison import compare_models, check_loo_reliability, model_averaging

check_diagnostics(idata)                       # R-hat, ESS, divergences, tree depth
create_diagnostic_report(idata, output_dir='diagnostics/')  # trace/rank/energy/ESS plots
compare_models({'m1': idata1, 'm2': idata2}, ic='loo')      # LOO/WAIC table
check_loo_reliability({'m1': idata1})          # Pareto-k checks (k>0.7 → use WAIC/k-fold)
```

LOO interpretation: Δloo < 2 ≈ tied (pick simpler); 4–10 moderate; > 10 strong evidence.

## Common Issues (quick fixes)

| Symptom | Fixes |
|---|---|
| Divergences (`idata.sample_stats.diverging.sum() > 0`) | `target_accept=0.95/0.99`; non-centered param.; stronger priors |
| Low ESS (< 400) | more `draws`; reparameterize; QR decomposition for correlated predictors |
| High R-hat (> 1.01) | longer chains; check multimodality; ADVI init |
| Slow sampling | ADVI init; more `cores`/`chains`; simplify model; VI |

Detailed troubleshooting: `references/workflows.md` and `references/sampling_inference.md`.

## Best Practices

- Standardize predictors; weakly informative (not flat) priors; named `dims`.
- Non-centered parameterization for hierarchies; prior predictive check before fitting.
- ≥4 chains; `random_seed` for reproducibility; `log_likelihood=True` for comparison.
- Validate with posterior predictive checks; report HDIs. Start simple, add complexity.

## Resources

- `references/workflows.md` — workflow cookbook + all model patterns + troubleshooting.
- `references/distributions.md` — distribution catalog and prior/likelihood selection.
- `references/sampling_inference.md` — NUTS/Metropolis/SMC, VI, MAP, reparameterization.
- `scripts/model_diagnostics.py` — `check_diagnostics()`, `create_diagnostic_report()`.
- `scripts/model_comparison.py` — `compare_models()`, `check_loo_reliability()`, `model_averaging()`.
- `assets/linear_regression_template.py`, `assets/hierarchical_model_template.py` — runnable templates.

## Notes

- Visualize structure with `pm.model_to_graphviz(model)`.
- Persist with `idata.to_netcdf('results.nc')` / `az.from_netcdf('results.nc')`.
- For very large models, consider minibatch ADVI or data subsampling.
