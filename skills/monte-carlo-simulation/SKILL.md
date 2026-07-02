---
name: monte-carlo-simulation
version: 0.1.0
description: Monte Carlo simulation for asset-price paths and portfolio risk metrics. Use when you need to project distributions of terminal wealth, compute path-dependent option payoffs, stress-test portfolios, or estimate VaR / CVaR by simulation. Covers parametric Geometric Brownian Motion, bootstrap (historical resampling), and block-bootstrap for serial-dependent returns. Library-agnostic — numpy + scipy as the base, with optional pyfolio for tearsheet summarization. For copula-based multi-asset joint sampling see copula-dependency; for closed-form VaR see value-at-risk. NOT for problems with analytic closed-form solutions (Black-Scholes, parametric VaR under joint normality) or IID bootstrap on serially-correlated data—use block bootstrap instead.
allowed-tools: Bash, Read, Edit, Write
license: BSD-3 (numpy/scipy)
metadata:
    skill-author: HyperFrequency
---

# Monte Carlo Simulation for Path & Risk Modeling

## Overview

Monte Carlo (MC) simulation answers the question "what is the distribution of outcomes if we repeat this process N times?" In quant finance the two dominant uses are: (1) **path simulation** — projecting one or many asset price paths forward under an assumed stochastic process (GBM, Heston, jump-diffusion) — and (2) **risk-metric estimation** — computing VaR, CVaR, drawdown, or terminal wealth quantiles by resampling historical returns (bootstrap MC) or sampling from a parametric model.

This skill is deliberately library-agnostic. The base toolkit is `numpy` (RNG, vectorized math) and `scipy.stats` (distributions). `pandas` for series handling. `arch.bootstrap` is mentioned for block bootstrap on serially-dependent data. `pyfolio` or `quantstats` for tearsheet summarization of simulated equity curves.

## When to Use This Skill

This skill should be used when:
- Projecting forward-looking distributions of cumulative returns or terminal wealth
- Pricing path-dependent derivatives (Asian, lookback, barrier options) where no closed form exists
- Estimating VaR / CVaR when the loss distribution is non-Gaussian or path-dependent
- Stress-testing a strategy across thousands of historical resamples (historical MC)
- Computing standard errors on backtest statistics via bootstrap
- Simulating portfolio paths under a known covariance / copula structure

Don't use MC when an analytic solution exists (Black-Scholes, parametric VaR under joint normality) — it's slower and noisier. Don't use plain (IID) bootstrap on serially-correlated data — use block bootstrap.

## Install / Setup

```bash
pip install numpy scipy pandas
# optional for block bootstrap:
pip install arch
# optional for tearsheets:
pip install quantstats pyfolio-reloaded
```

No special config. Use a seeded `np.random.default_rng(seed)` for reproducibility.

## Minimal Example — Two-Style Monte Carlo

### Parametric GBM path simulation

```python
import numpy as np

def simulate_gbm(S0, mu, sigma, T, n_steps, n_paths, seed=None):
    """
    Geometric Brownian Motion: dS_t = mu * S_t dt + sigma * S_t dW_t.
    Exact (log-space) discretization — no Euler error.

    Returns paths of shape (n_paths, n_steps + 1).
    """
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    # log-returns increments
    drift = (mu - 0.5 * sigma ** 2) * dt
    shock = sigma * np.sqrt(dt) * rng.standard_normal((n_paths, n_steps))
    log_paths = np.concatenate(
        [np.zeros((n_paths, 1)), np.cumsum(drift + shock, axis=1)], axis=1
    )
    return S0 * np.exp(log_paths)

paths = simulate_gbm(S0=100.0, mu=0.07, sigma=0.20, T=1.0,
                     n_steps=252, n_paths=10_000, seed=42)

terminal = paths[:, -1]
print(f"Mean terminal: {terminal.mean():.2f}")
print(f"5% quantile (terminal-wealth VaR cutoff): {np.quantile(terminal, 0.05):.2f}")
print(f"95% quantile: {np.quantile(terminal, 0.95):.2f}")
```

### Historical bootstrap MC for portfolio P&L distribution

```python
import numpy as np

def bootstrap_pnl(returns, horizon_days, n_sims, seed=None):
    """
    IID bootstrap: resample returns with replacement and compound.
    Assumes returns are approximately serially independent.
    For serial-dependent series use block bootstrap (arch.bootstrap.StationaryBootstrap).
    """
    rng = np.random.default_rng(seed)
    sampled = rng.choice(returns, size=(n_sims, horizon_days), replace=True)
    cum_returns = np.prod(1 + sampled, axis=1) - 1
    return cum_returns

# 1 year of synthetic daily returns
historical_returns = np.random.default_rng(0).standard_normal(252 * 5) * 0.012 + 0.0003
pnl_dist = bootstrap_pnl(historical_returns, horizon_days=21, n_sims=50_000, seed=7)
var_95 = -np.quantile(pnl_dist, 0.05)
cvar_95 = -pnl_dist[pnl_dist <= np.quantile(pnl_dist, 0.05)].mean()
print(f"21-day 95% VaR:  {var_95:.4f}")
print(f"21-day 95% CVaR: {cvar_95:.4f}")
```

## Key API Surface

| Tool | Purpose |
|---|---|
| `np.random.default_rng(seed)` | Modern numpy RNG (PCG64). Prefer over legacy `np.random.*`. |
| `rng.standard_normal(shape)` | Gaussian shocks for GBM / Heston |
| `rng.choice(x, size, replace=True)` | IID bootstrap resampling |
| `np.quantile(x, q)` | Empirical quantiles for VaR cutoffs |
| `scipy.stats.norm / t / skewnorm` | Parametric draws for non-Gaussian shocks |
| `scipy.stats.multivariate_normal.rvs(mean, cov, size)` | Correlated multi-asset shocks (when copula is Gaussian) |
| `arch.bootstrap.StationaryBootstrap(block_size, *series)` | Block bootstrap preserving serial dependence  // unverified — see https://arch.readthedocs.io/en/latest/bootstrap/index.html |
| `quantstats.reports.html(returns, output=...)` | Tearsheet for a simulated equity curve |
| `pyfolio.tears.create_returns_tear_sheet(returns)` | Alternative tearsheet (pyfolio is dormant; prefer quantstats) |

## Interpreting the Output

- **Standard error scales with `1/sqrt(N)`.** Going from 1,000 to 10,000 paths cuts MC noise by ~3.16x, not 10x. For 95% VaR estimates with reasonable precision, target **at least 10,000–50,000 paths**; for 99% tail metrics, **100,000+**.
- **Convergence check:** plot the running mean / running quantile of your statistic against `n_paths`. It should stabilize. If it's still drifting at the end of your simulation, your N is too small.
- **Quantile vs. expected-shortfall variance.** Quantiles (VaR) are noisier in the tails than the mean (CVaR / ES). For the same `n_paths`, expect wider confidence bands on `np.quantile(x, 0.99)` than on the conditional mean below it.
- **GBM sanity:** terminal-price mean should approximate `S0 * exp(mu * T)` within MC noise; log-return variance should approximate `sigma**2 * T`. If they don't, you have a bug in the discretization.
- **Bootstrap reproducibility:** always pass `seed=` to `default_rng`. A common embarrassment is publishing a backtest result that nobody can reproduce.

## Block Bootstrap for Serially-Dependent Returns

When returns have autocorrelation (especially in squared returns / volatility), IID bootstrap destroys the dependence. Use stationary or moving-block bootstrap:

```python
import numpy as np
from arch.bootstrap import StationaryBootstrap   # // unverified — see arch docs link below

returns = np.random.default_rng(0).standard_normal(252 * 5) * 0.012

# Stationary bootstrap with mean block length = 10 days.
bs = StationaryBootstrap(10, returns)
sims = []
for data in bs.bootstrap(5_000):
    # `data` is ((resampled_returns,), {}); compound to terminal wealth.
    r = data[0][0]
    sims.append(np.prod(1 + r) - 1)
sims = np.array(sims)
print(f"95% block-bootstrap VaR: {-np.quantile(sims, 0.05):.4f}")
```

Mean block length is the only tuning knob; rule of thumb is `O(n^{1/3})` for `n` observations, but 5-20 days is reasonable for daily financial data. Validate by comparing the ACF of resampled returns to the empirical ACF — they should match.

## Variance Reduction Techniques (Brief)

For path-pricing problems where MC noise is the bottleneck, three standard tricks:

- **Antithetic variates:** for every `Z` you draw, also use `-Z`. Halves variance for symmetric payoffs at near-zero cost.
- **Control variates:** simulate both the target payoff and a known-mean payoff (e.g. the underlying terminal price); regress the difference. Highly effective for options with a Black-Scholes analog.
- **Quasi-Monte Carlo (QMC):** replace `rng.standard_normal` with low-discrepancy sequences (`scipy.stats.qmc.Sobol`). Converges as `O(1/N)` rather than `O(1/sqrt(N))` in low dimensions. Works less well past ~20 dimensions.

```python
from scipy.stats import qmc
sobol = qmc.Sobol(d=252, scramble=True, seed=0)
u = sobol.random(n=4096)                        # shape (4096, 252)
from scipy.stats import norm
z = norm.ppf(u)                                  # transform to Gaussian
# use `z` instead of rng.standard_normal((4096, 252)) in the GBM step
```

## Common Pitfalls

1. **IID bootstrap on serially dependent returns.** Daily equity returns have weak autocorrelation but daily *squared* returns (volatility) have strong autocorrelation. IID bootstrap destroys this structure and **understates** drawdown risk. Use `arch.bootstrap.StationaryBootstrap` or moving-block bootstrap. See the block bootstrap section above for a working pattern.
2. **Discretization error in Euler-scheme GBM.** `S_{t+dt} = S_t * (1 + mu*dt + sigma*sqrt(dt)*Z)` has O(dt) bias and can go negative for large `dt`. Use the **log-space exact** scheme: `S_{t+dt} = S_t * exp((mu - 0.5*sigma**2)*dt + sigma*sqrt(dt)*Z)`. Same speed, no bias, never negative.
3. **Too few paths in the tail.** Estimating 99% VaR from 1,000 paths uses only 10 observations in the tail. The estimate is noisy and biased. Use at least 50,000 paths for 99% VaR, more for 99.5%.
4. **Confusing arithmetic and log returns.** Cumulating arithmetic returns with `np.prod(1+r)` is correct for terminal wealth. Cumulating with `np.sum(r)` only works for log returns. Mixing the two silently gives wrong answers, especially over multi-month horizons.
5. **Forgetting the drift.** Plain GBM with `mu=0` is a martingale and the **median** terminal price drifts *down* even though the mean stays at `S0`. For risk-neutral pricing this is correct; for real-world scenario simulation you almost always want `mu > 0` to match historical equity risk premium.
6. **Reusing the same RNG seed across "independent" simulations.** Running 100 strategies each with `seed=42` couples their shocks. Either seed once at the top of the script, or use `rng.spawn(100)` (Python 3.12+ / numpy 1.25+) for independent substreams.

## Multi-Asset Correlated Paths

For a portfolio MC with linear correlation, use the Cholesky factor of the covariance matrix to inject correlated shocks. For non-Gaussian dependence (tail-coupled assets), use a copula — see the `copula-dependency` skill.

```python
import numpy as np

def simulate_correlated_gbm(S0, mu, sigma, corr, T, n_steps, n_paths, seed=None):
    """
    Vectorized multi-asset GBM with linear correlation.

    Parameters
    ----------
    S0    : (d,) initial prices
    mu    : (d,) drifts
    sigma : (d,) volatilities
    corr  : (d, d) correlation matrix (must be PSD)

    Returns paths of shape (n_paths, n_steps + 1, d).
    """
    rng = np.random.default_rng(seed)
    d = len(S0)
    dt = T / n_steps
    L = np.linalg.cholesky(corr)                                        # (d, d)
    Z = rng.standard_normal((n_paths, n_steps, d))                      # IID Gaussian
    shocks = Z @ L.T                                                    # correlated
    drift = (mu - 0.5 * sigma ** 2) * dt                                 # (d,)
    diffusion = sigma * np.sqrt(dt) * shocks                            # broadcast
    log_increments = drift + diffusion
    log_paths = np.concatenate(
        [np.zeros((n_paths, 1, d)), np.cumsum(log_increments, axis=1)], axis=1
    )
    return S0 * np.exp(log_paths)
```

This is sufficient under joint-Gaussian dependence. For heavy-tailed joint behavior, generate the copula samples first (per `copula-dependency`), then apply the inverse marginal CDFs to map them into return space.

## References

### Primary library
- [NumPy on GitHub](https://github.com/numpy/numpy) — upstream repo + issues
- [NumPy `random` module docs](https://numpy.org/doc/stable/reference/random/index.html) — Generator vs legacy RandomState; verified against numpy 2.x
- [SciPy on GitHub](https://github.com/scipy/scipy) — `scipy.stats` source of truth
- [arch on GitHub](https://github.com/bashtage/arch) — for the bootstrap submodule used in block resampling
- [quantstats](https://github.com/ranaroussi/quantstats) — tearsheets for simulated equity curves

### Deep-dive docs (specific pages worth bookmarking)
- [NumPy `default_rng` and `Generator`](https://numpy.org/doc/stable/reference/random/generator.html) — modern PCG64 RNG; the `rng.standard_normal` / `rng.choice` / `rng.spawn` calls used throughout
- [SciPy quasi-Monte Carlo (`scipy.stats.qmc`)](https://docs.scipy.org/doc/scipy/reference/stats.qmc.html) — Sobol / Halton sequences for variance-reduced GBM
- [SciPy `multivariate_normal`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.multivariate_normal.html) — the `rvs` method for correlated Gaussian shocks
- [`arch.bootstrap.StationaryBootstrap`](https://arch.readthedocs.io/en/latest/bootstrap/parametric-bootstrap.html) — Politis-Romano stationary bootstrap with random block lengths
- [`arch.bootstrap.MovingBlockBootstrap`](https://arch.readthedocs.io/en/latest/bootstrap/iid-bootstrap.html) — fixed-block alternative
- [`arch.bootstrap.optimal_block_length`](https://arch.readthedocs.io/en/latest/bootstrap/generated/arch.bootstrap.optimal_block_length.html) — Politis-White automatic block-length selector

### Adjacent / alternative libraries
- [QuantLib-Python](https://github.com/lballabio/QuantLib-SWIG) — production-grade Monte Carlo engine with built-in low-discrepancy sequences, Heston/Bates models, exotic-option payoffs
- [pyfolio-reloaded](https://github.com/stefan-jansen/pyfolio-reloaded) — drop-in fork of the dormant Quantopian pyfolio for tearsheet aggregation
- [riskfolio-lib](https://github.com/dcajasn/Riskfolio-Lib) — portfolio MC + CVaR / scenario optimization
- [arch.bootstrap.IIDBootstrap / CircularBlockBootstrap](https://arch.readthedocs.io/en/latest/bootstrap/iid-bootstrap.html) — alternative resamplers when stationary blocks aren't right

### Academic papers
- Boyle, P., Broadie, M., & Glasserman, P. (1997). "Monte Carlo Methods for Security Pricing." *Journal of Economic Dynamics and Control* 21(8-9), 1267-1321. [DOI: 10.1016/S0165-1889(97)00028-6](https://doi.org/10.1016/S0165-1889(97)00028-6) — the canonical survey of variance reduction (antithetic, control variates, QMC).
- Politis, D. N., & Romano, J. P. (1994). "The Stationary Bootstrap." *Journal of the American Statistical Association* 89(428), 1303-1313. [DOI: 10.1080/01621459.1994.10476870](https://doi.org/10.1080/01621459.1994.10476870) — the resampler that `arch.bootstrap.StationaryBootstrap` implements.
- Glasserman, P. (2003). *Monte Carlo Methods in Financial Engineering*. Springer. [DOI: 10.1007/978-0-387-21617-1](https://doi.org/10.1007/978-0-387-21617-1) — the reference text for GBM, variance reduction, importance sampling, Heston discretization.
- Hansen, P. R., Lunde, A., & Nason, J. M. (2011). "The Model Confidence Set." *Econometrica* 79(2), 453-497. [DOI: 10.3982/ECTA5771](https://doi.org/10.3982/ECTA5771) — used to compare MC-based forecasting models on equal footing.

### Tutorials & write-ups
- [NumPy "Random sampling" guide](https://numpy.org/doc/stable/reference/random/index.html#quick-start) — covers `default_rng`, parallel generators, spawning
- [SciPy QMC tutorial](https://docs.scipy.org/doc/scipy/tutorial/stats/sampling.html) — practical recipes for Sobol/Halton in path simulation
- [arch bootstrap examples notebook](https://nbviewer.org/github/bashtage/arch/blob/main/examples/bootstrap_examples.ipynb) — Kevin Sheppard's walkthrough of every bootstrap variant on financial data

### Standard datasets / benchmarks
- Synthetic GBM with known closed-form solution — mean terminal `S0 * exp(mu * T)`, variance `S0^2 * exp(2mu*T)*(exp(sigma^2*T)-1)`; the only fully-controlled MC benchmark
- Heston jump-diffusion calibrated to S&P 500 — see Glasserman (2003) Ch. 3 for parameters; useful for testing variance-reduction techniques

### Last cross-checked
2026-05-20 — via Context7 `/ranaroussi/quantstats` + `/bashtage/arch` + WebSearch verification of all paper DOIs.
