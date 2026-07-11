# Model Comparison and Evidence

Comparing the best-fit likelihoods of two models is not model comparison: a more
flexible model almost always fits the data better. Proper Bayesian comparison
penalizes complexity, either through predictive information criteria (WAIC/LOO)
or through the marginal likelihood (evidence, Bayes factors).

## What NOT to do

```python
# Insufficient on its own: no complexity penalty, rewards overfitting.
log_probs = sampler.get_log_prob(discard=1000, flat=True)
print("max log L:", log_probs.max())
```

Use max/mean log-likelihood only as a rough smell test, never as the deciding
criterion.

## Information criteria: WAIC and LOO (recommended default)

WAIC and PSIS-LOO estimate out-of-sample predictive accuracy from the posterior
and are the practical default for comparison. Both need the **pointwise**
log-likelihood (one value per data point per posterior draw), not the summed
log-likelihood.

With emcee, compute the per-point log-likelihood and store it as a *blob* so it
travels with the chain:

```python
def log_probability(theta, t, y, yerr):
    lp = log_prior(theta)
    if not np.isfinite(lp):
        return -np.inf, np.full_like(y, -np.inf)   # (logpost, pointwise_loglik)
    y_model = model(t, *theta)
    pointwise = -0.5 * (((y - y_model) / yerr)**2 + np.log(2*np.pi*yerr**2))
    return lp + pointwise.sum(), pointwise
```

`sampler.get_blobs()` then holds the pointwise log-likelihood array. Hand the
chain plus blobs to ArviZ (`az.from_emcee` exposes `blob_names`/`blob_groups` for
attaching a `log_likelihood` group — check its current signature) and compare:

```python
import arviz as az
az.loo(idata)                                  # PSIS-LOO with Pareto-k reliability
az.waic(idata)
az.compare({"model_a": idata_a, "model_b": idata_b}, ic="loo")
```

Interpretation:

- Rank by `elpd_loo` (higher is better). A difference `dloo` below ~2 is
  effectively tied — prefer the simpler model. 4-10 is moderate evidence, > 10
  strong.
- Check Pareto-k values. Any `k > 0.7` means LOO is unreliable for that point;
  fall back to WAIC or k-fold cross-validation.

`pymc` computes all of this natively (`idata_kwargs={'log_likelihood': True}`
then `az.compare`); if you are already in a PyMC model, prefer that path.

## Marginal likelihood, evidence, and Bayes factors

The Bayes factor is the ratio of marginal likelihoods (evidences):

```
BF_10 = Z_1 / Z_0 = P(data | model_1) / P(data | model_0)
```

Unlike WAIC/LOO it answers "which model does the data support", integrating over
the whole prior. It is also far harder to compute reliably.

### Do not use the harmonic-mean estimator

Estimating `Z` from `1 / mean(1 / L)` over posterior samples is notoriously
unstable — its variance is often infinite and it silently favors overfit models.
Avoid it despite how easy it looks.

### Nested sampling with dynesty (reliable evidence)

Nested sampling computes `Z` and its uncertainty directly, and gives posterior
samples as a by-product. You supply the likelihood and a **prior transform** that
maps a unit cube `[0,1]^ndim` to your prior.

```python
import numpy as np
from dynesty import NestedSampler

def prior_transform(u):
    # Map unit cube -> uniform priors matching the emcee box prior
    lo = np.array([0.0, 0.0, 0.0])
    hi = np.array([10.0, 5.0, 10.0])
    return lo + u * (hi - lo)

def loglike(theta):
    return log_likelihood(theta, t_data, y_data, y_err)  # NO prior term here

sampler = NestedSampler(loglike, prior_transform, ndim=3)
sampler.run_nested()
res = sampler.results
log_Z, log_Z_err = res.logz[-1], res.logzerr[-1]
print(f"log Z = {log_Z:.2f} +/- {log_Z_err:.2f}")
```

- Use `dynesty.DynamicNestedSampler` when you want to allocate more live points to
  the posterior bulk (better parameter estimates) or to the evidence.
- The log Bayes factor between two models is `log_Z_1 - log_Z_0`; propagate both
  `logzerr` values into its uncertainty.
- Posterior samples come from `res.samples` weighted by `res.importance_weights()`
  (older dynesty: derive weights from `res.logwt` / `res.logz`); resample to equal
  weight with `dynesty.utils.resample_equal` before making a corner plot.

### Jeffreys scale for `log10` Bayes factor

| `log10 BF_10` | Evidence for model 1 |
|---|---|
| 0 - 0.5 | Not worth more than a bare mention |
| 0.5 - 1 | Substantial |
| 1 - 2 | Strong |
| > 2 | Decisive |

Bayes factors are sensitive to prior width (unlike parameter estimates). Report
the priors you used, and check robustness to reasonable prior changes before
claiming a decisive result.

## Choosing a comparison method

- **Nested models, predictive question, weak priors:** WAIC / PSIS-LOO.
- **Non-nested models, genuine "which hypothesis" question, defensible priors:**
  Bayes factor via nested sampling.
- **Already in PyMC:** use its built-in `az.compare` path — see the `pymc` skill.
