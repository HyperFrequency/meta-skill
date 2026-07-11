# emcee Workflow: End-to-End MCMC

`emcee` implements the affine-invariant ensemble sampler of Goodman & Weare. It
is a good default when you have a custom Python likelihood, a handful to a few
dozen parameters, and no analytic gradients. This file is a complete, runnable
template you can adapt one block at a time.

## 1. Model, data, and the log-probability

The sampler only ever needs one callable: a log-posterior up to an additive
constant. Build it from an explicit `log_prior + log_likelihood` so each piece
is testable in isolation.

```python
import numpy as np
import emcee

# Forward model: damped oscillator
def model(t, amplitude, damping_rate, angular_freq):
    return amplitude * np.exp(-damping_rate * t) * np.cos(angular_freq * t)

# Synthetic data with known ground truth (swap in your real arrays)
rng = np.random.default_rng(0)
t_data = np.linspace(0, 10, 50)
true_params = np.array([2.0, 0.3, 1.5])   # amplitude, damping_rate, angular_freq
y_err = 0.1 * np.ones_like(t_data)
y_data = model(t_data, *true_params) + y_err * rng.standard_normal(t_data.size)

def log_prior(theta):
    amplitude, damping_rate, angular_freq = theta
    # Uniform priors inside a box, -inf outside
    inside = (0.0 < amplitude < 10.0
              and 0.0 < damping_rate < 5.0
              and 0.0 < angular_freq < 10.0)
    return 0.0 if inside else -np.inf

def log_likelihood(theta, t, y, yerr):
    y_model = model(t, *theta)
    residual = (y - y_model) / yerr
    # Full Gaussian log-likelihood (the constant matters for model comparison)
    return -0.5 * np.sum(residual**2 + np.log(2 * np.pi * yerr**2))

def log_probability(theta, t, y, yerr):
    lp = log_prior(theta)
    if not np.isfinite(lp):
        return -np.inf                      # short-circuit: skip the likelihood
    return lp + log_likelihood(theta, t, y, yerr)
```

Notes:

- Keep the full Gaussian normalization (`+ np.log(2*pi*yerr**2)`). Dropping it is
  fine for parameter estimation but corrupts evidence and information-criterion
  comparisons.
- Return `-np.inf` (not `NaN`) for zero-prior regions; the ensemble sampler
  handles `-inf` but will error on `NaN`.
- If `yerr` itself is a free parameter (fitting for the noise level), add it to
  `theta` and include its `log(2*pi*sigma^2)` term — this is often the right fix
  when least-squares error bars look wrong.

## 2. Initialize walkers and run

```python
ndim = 3
nwalkers = 32                                # >= 2*ndim, 4*ndim is safer

# Start walkers in a tight Gaussian ball near a point estimate (e.g. a
# curve_fit MAP). A tiny spread avoids walkers landing in -inf prior regions.
start = true_params + 1e-2 * rng.standard_normal((nwalkers, ndim))

sampler = emcee.EnsembleSampler(
    nwalkers, ndim, log_probability, args=(t_data, y_data, y_err),
)
sampler.run_mcmc(start, 5000, progress=True)
```

- `nwalkers` must be even and `>= 2 * ndim`. More walkers explore multimodal or
  correlated posteriors better but cost proportionally more likelihood calls.
- Poor initialization (walkers in a `-inf` region) makes `run_mcmc` raise
  "Probability function returned NaN"; verify `np.isfinite(log_probability(start[i], ...))`
  for every walker before running.

## 3. Burn-in, thinning, flat samples

Set burn-in and thinning from the autocorrelation time (see
`diagnostics.md`), not from round numbers. As a rule of thumb discard
`~2-3 * tau_max` and thin by `~0.5 * tau_min`.

```python
flat_samples = sampler.get_chain(discard=1000, thin=15, flat=True)
log_probs = sampler.get_log_prob(discard=1000, thin=15, flat=True)
print("posterior samples:", flat_samples.shape[0])
```

## 4. Corner plot and credible intervals

`corner` renders the marginal and pairwise-joint posterior. The 16/50/84
percentiles give the median and a 68% credible interval.

```python
import corner

labels = [r"$A$", r"$\gamma$", r"$\omega$"]
fig = corner.corner(
    flat_samples, labels=labels, truths=true_params,
    quantiles=[0.16, 0.5, 0.84], show_titles=True,
)
fig.savefig("corner.png", dpi=150, bbox_inches="tight")

for i, name in enumerate(labels):
    lo, mid, hi = np.percentile(flat_samples[:, i], [16, 50, 84])
    print(f"{name} = {mid:.4f} (+{hi-mid:.4f} / -{mid-lo:.4f})")
```

Report the credible interval, not a bare "±". Asymmetric intervals are a signal
that a Gaussian error bar would have been misleading — one of the main reasons to
run MCMC at all.

## 5. Posterior predictive check

Overplot model curves drawn from the posterior against the data. Systematic
misfit here means the *model*, not the sampler, is wrong.

```python
import matplotlib.pyplot as plt

t_grid = np.linspace(0, 12, 200)
draws = flat_samples[rng.integers(flat_samples.shape[0], size=200)]

fig, ax = plt.subplots(figsize=(9, 5))
for theta in draws:
    ax.plot(t_grid, model(t_grid, *theta), color="C3", alpha=0.03)
ax.errorbar(t_data, y_data, yerr=y_err, fmt="ko", capsize=3, label="data")
ax.set_xlabel("time"); ax.set_ylabel("y"); ax.legend()
fig.savefig("posterior_predictive.png", dpi=150, bbox_inches="tight")
```

## 6. Scaling up: pools, backends, moves

- **Parallelism.** Pass a `pool` to distribute likelihood calls. The sampler is
  embarrassingly parallel across walkers within a step.

  ```python
  from multiprocessing import Pool
  with Pool() as pool:
      sampler = emcee.EnsembleSampler(
          nwalkers, ndim, log_probability,
          args=(t_data, y_data, y_err), pool=pool,
      )
      sampler.run_mcmc(start, 5000, progress=True)
  ```

  For this to help, the likelihood must dominate the per-step cost and be
  picklable (module-level function, no captured un-picklable state).

- **Checkpointing.** Persist the chain to disk so a long run can resume:

  ```python
  backend = emcee.backends.HDFBackend("chain.h5")
  backend.reset(nwalkers, ndim)
  sampler = emcee.EnsembleSampler(nwalkers, ndim, log_probability,
                                  args=(t_data, y_data, y_err), backend=backend)
  ```

  Reopen later with `emcee.backends.HDFBackend("chain.h5")` (no `reset`) and read
  `get_chain()` without re-running.

- **Moves.** The default stretch move (`emcee.moves.StretchMove`) struggles when
  parameters are strongly correlated. A differential-evolution mix often helps:

  ```python
  moves = [(emcee.moves.DEMove(), 0.8), (emcee.moves.DESnookerMove(), 0.2)]
  sampler = emcee.EnsembleSampler(nwalkers, ndim, log_probability,
                                  args=(t_data, y_data, y_err), moves=moves)
  ```

  Reparameterizing (e.g. sampling `log`-scale positive parameters, or rotating
  into decorrelated coordinates) usually beats any move choice.

## When emcee is the wrong tool

- **Gradients available / high dimensions (> ~20-50 params):** use gradient-based
  NUTS via the `pymc` skill. Ensemble methods degrade as dimension grows.
- **Sharp multimodality / you need the evidence Z:** use nested sampling
  (`dynesty`, see `model-comparison.md`).
- **Cheap unimodal likelihood, point estimate is enough:** `scipy.optimize`
  least-squares is far faster.
