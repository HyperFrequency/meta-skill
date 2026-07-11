---
name: bayesian-inference
version: 0.1.0
description: >-
  Full Bayesian parameter estimation via MCMC — recover posterior distributions,
  credible intervals, and joint parameter correlations instead of point
  estimates. Centers on emcee (affine-invariant ensemble sampler) for custom
  Python likelihoods, with convergence diagnostics (integrated autocorrelation
  time, rank-normalized R-hat and ESS via ArviZ), corner plots, posterior
  predictive checks, and model comparison (WAIC/LOO, Bayes factors, nested
  sampling with dynesty). Use when you need the whole posterior, parameters are
  correlated, prior information should be folded in, or least-squares error bars
  look untrustworthy. Do NOT use when a curve_fit with error bars suffices, when
  you have hundreds of parameters (reach for variational inference), or when the
  likelihood is cheap and a fast point estimate is all you need. For high-level
  probabilistic programming with NUTS use `pymc`; for frequentist regression use
  `statsmodels` or `scikit-learn`.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: "emcee: MIT; corner: BSD-3-Clause"
---

# Bayesian Inference with MCMC

## Overview

Estimate parameters by sampling the full posterior rather than optimizing to a
single best fit. You get marginal and joint distributions, honest (often
asymmetric) credible intervals, and a principled way to fold in prior knowledge
and compare models. This skill focuses on `emcee`, the affine-invariant ensemble
sampler — the right tool for a custom Python likelihood with a handful to a few
dozen parameters and no analytic gradients.

This file is a lean router. The runnable depth lives in `references/`:

- `references/emcee-workflow.md` — end-to-end template: log-prob construction,
  walker init, burn-in/thinning, corner plots, posterior predictive checks,
  parallel pools, HDF checkpointing, custom moves.
- `references/diagnostics.md` — autocorrelation time, acceptance fraction, the
  ArviZ R-hat/ESS bridge, trace-plot reading, the walkers-aren't-chains caveat.
- `references/model-comparison.md` — WAIC/PSIS-LOO, Bayes factors, the
  harmonic-mean warning, nested sampling with dynesty, the Jeffreys scale.

## When to Use This Skill

- You need the full posterior distribution, not just point estimates + error bars.
- Parameters are correlated and you want the joint (not marginal-only) picture.
- Prior information exists and should be incorporated explicitly.
- Least-squares / `curve_fit` error bars look unreliable or implausibly symmetric.
- You want to compare models via information criteria or Bayesian evidence.

## When NOT to Use This Skill

- A `scipy.optimize.curve_fit` with error bars is genuinely sufficient — it is
  much faster, so start there and escalate only if it fails.
- You have gradients and/or many parameters (> ~20-50): use gradient-based NUTS
  via the `pymc` skill instead of an ensemble sampler.
- The likelihood is cheap and unimodal and you only need a point estimate.
- You want frequentist regression with coefficient tables → `statsmodels` or
  `scikit-learn`.

## Core Idea: build one log-posterior

The sampler needs a single callable returning `log(prior) + log(likelihood)` up
to a constant. Keep the two pieces separate so each is testable.

```python
def log_probability(theta, t, y, yerr):
    lp = log_prior(theta)                 # -inf outside prior bounds
    if not np.isfinite(lp):
        return -np.inf                    # short-circuit; never return NaN
    return lp + log_likelihood(theta, t, y, yerr)
```

Keep the full Gaussian normalization in `log_likelihood` (the `log(2*pi*sigma^2)`
term) — dropping it is harmless for estimation but corrupts model comparison.
Full model + prior + likelihood code: `references/emcee-workflow.md`.

## Minimal emcee run

```python
import emcee, numpy as np

ndim, nwalkers = 3, 32                     # nwalkers even and >= 2*ndim (4x safer)
start = map_estimate + 1e-2 * np.random.randn(nwalkers, ndim)  # tight ball near MAP

sampler = emcee.EnsembleSampler(nwalkers, ndim, log_probability,
                                args=(t_data, y_data, y_err))
sampler.run_mcmc(start, 5000, progress=True)

flat = sampler.get_chain(discard=1000, thin=15, flat=True)     # (nsamples, ndim)
```

Set `discard` and `thin` from the autocorrelation time, not round numbers — see
diagnostics below.

## Report the posterior, not a point

```python
import corner
fig = corner.corner(flat, labels=labels, quantiles=[0.16, 0.5, 0.84],
                    show_titles=True)      # marginals + pairwise joints

for i, name in enumerate(labels):          # 68% credible interval per parameter
    lo, mid, hi = np.percentile(flat[:, i], [16, 50, 84])
    print(f"{name} = {mid:.4f} (+{hi-mid:.4f} / -{mid-lo:.4f})")
```

Then run a **posterior predictive check** — overplot model curves drawn from the
posterior against the data. Full example in `references/emcee-workflow.md`.

## Always Check Convergence

A posterior you did not diagnose is a guess. Minimum gates before trusting any
interval (details and code in `references/diagnostics.md`):

1. **Autocorrelation time** — `sampler.get_autocorr_time()`; require chain length
   `> ~50 * tau`. Handle `emcee.autocorr.AutocorrError` (chain too short → run
   longer).
2. **Acceptance fraction** — `np.mean(sampler.acceptance_fraction)` in ~0.2-0.5.
3. **R-hat and ESS via ArviZ** — `az.from_emcee(sampler)` then `az.summary`;
   require `r_hat < 1.01` and `ess_bulk > 400`. Do *not* hand-roll Gelman-Rubin
   across emcee walkers — they are not independent chains.
4. **Trace + rank plots** — stationary fuzz, no drift, uniform rank histograms.

## Model Comparison

Comparing best-fit likelihoods rewards overfitting. Use predictive information
criteria or the evidence instead (see `references/model-comparison.md`):

- **WAIC / PSIS-LOO** (default) via ArviZ — needs pointwise log-likelihood; store
  it from emcee as a *blob*, then `az.compare({...}, ic="loo")`. Watch Pareto-k.
- **Bayes factors / evidence Z** — compute with **nested sampling** (`dynesty`),
  never the harmonic-mean estimator. Log Bayes factor = `log_Z_1 - log_Z_0`.
- If you are already in a PyMC model, use its native `az.compare` path — `pymc`.

## Failure Modes and Fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Walkers stuck, acceptance ~0 | Prior too tight or likelihood too peaked | Widen priors; reparameterize; init near MAP |
| `tau` huge / slow convergence | Strongly correlated parameters | Sample in log-space; decorrelate; try `DEMove` |
| Corner plot has hard straight edges | Prior bounds clipping the posterior | Widen the prior box |
| Trace drifts / never flattens | Not converged | Run longer; discard more burn-in |
| Posterior is bimodal / walkers split | Genuine multimodality | Parallel tempering or nested sampling |
| `run_mcmc` errors on NaN | A walker started in a `-inf` region | Verify `isfinite(log_probability(start[i]))` for all walkers |
| LOO Pareto-k > 0.7 | Influential points break PSIS | Use WAIC or k-fold cross-validation |

## Related Skills

- `pymc` — high-level probabilistic programming with NUTS/ADVI; use for
  gradient-based sampling, hierarchical models, and many parameters.
- `statsmodels`, `scikit-learn` — frequentist regression and predictive ML when
  you do not need a posterior.
- `shap` — attribution/explanations for fitted predictive models (different goal).
