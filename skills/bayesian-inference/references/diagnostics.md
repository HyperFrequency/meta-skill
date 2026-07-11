# Convergence Diagnostics

A posterior you did not check is a guess. Before you trust any credible interval,
confirm the sampler mixed. For `emcee` the primary diagnostic is the integrated
autocorrelation time; rank-normalized R-hat and effective sample size (via
ArviZ) are the cross-checks.

## Integrated autocorrelation time (the emcee-native check)

The autocorrelation time `tau` estimates how many steps the chain takes to
produce one independent sample. The standard reliability rule is:

> Run until the chain is at least ~50 * tau long.

```python
try:
    tau = sampler.get_autocorr_time()          # raises if chain is too short
    print("tau:", tau)
    print("chain length / tau:", sampler.iteration / tau)  # want > 50
except emcee.autocorr.AutocorrError as err:
    # Chain is shorter than ~50*tau; the estimate is unreliable.
    print("run longer:", err)
    tau = sampler.get_autocorr_time(tol=0)     # tol=0 returns the estimate anyway
```

- Set burn-in `discard >= 2-3 * max(tau)` and thinning `thin >= 0.5 * min(tau)`.
- A long or slowly-converging `tau` almost always means correlated parameters —
  reparameterize (log-space positive scales, decorrelate) rather than just
  running longer.

## Acceptance fraction

```python
print("mean acceptance fraction:", np.mean(sampler.acceptance_fraction))
```

Aim for roughly 0.2-0.5. Near zero means walkers are stuck (prior too tight, or
the likelihood is too peaked for the current parameterization); near one means
steps are too timid and mixing is slow.

## ArviZ bridge: R-hat and ESS

Convert the emcee sampler into an `InferenceData` object and use ArviZ's
rank-normalized, split diagnostics — these are the modern standard and are more
robust than a hand-rolled Gelman-Rubin.

```python
import arviz as az

idata = az.from_emcee(sampler, var_names=["amplitude", "damping_rate", "angular_freq"])
print(az.summary(idata))          # per-parameter mean, sd, hdi, r_hat, ess_bulk, ess_tail
az.plot_trace(idata)              # marginals + trace, one row per parameter
az.plot_rank(idata)              # rank plots: uniform histograms == good mixing
```

Gates to require before reporting results:

- `r_hat < 1.01` for every parameter.
- `ess_bulk > 400` (and `ess_tail > 400` if you quote tail quantiles).
- Trace plots show stationary "fuzzy caterpillars" with no drift; rank plots are
  roughly uniform across chains.

### Why not naive Gelman-Rubin across walkers

emcee's walkers are **not** independent MCMC chains — they interact each step, so
treating each walker as a separate chain and applying textbook Gelman-Rubin
underestimates between-chain variance and can report a falsely reassuring R-hat.
Prefer `az.from_emcee` + `az.rhat` (which reshapes appropriately) or, if you need
a hand computation, split each walker's chain in half along the step axis and
compute rank-normalized split-R-hat. The manual formula below is included only
for intuition, not as the diagnostic of record:

```python
# Illustrative only — prefer az.rhat on a proper (chain, draw) reshape.
chain = sampler.get_chain(discard=1000)        # (steps, walkers, ndim)
n_steps = chain.shape[0]
means = chain.mean(axis=0)                      # (walkers, ndim)
between = n_steps * means.var(axis=0, ddof=1)
within = chain.var(axis=0, ddof=1).mean(axis=0)
var_est = (1 - 1/n_steps) * within + between / n_steps
r_hat = np.sqrt(var_est / within)               # want < 1.01
```

## Reading trace plots

| Trace pattern | Interpretation | Action |
|---|---|---|
| Stationary fuzz around a level | Converged, good mixing | Proceed |
| Slow drift / trend | Not converged (still burning in) | Run longer, discard more |
| Wanders between two levels | Multimodal posterior | Parallel tempering / nested sampling |
| Long flat runs then jumps | Poor mixing, high autocorrelation | Reparameterize, change moves |
| Some walkers stuck off to the side | Bad initialization / lost walkers | Re-init near MAP; check per-walker `acceptance_fraction` |

## Effective-sample-size sanity numbers

The number of *independent* posterior samples is roughly
`nwalkers * (nsteps - burnin) / tau`. If a 68% credible interval is enough you
need only a few hundred effective samples; for well-resolved tail quantiles
(e.g. 99%) push `ess_tail` into the thousands.
