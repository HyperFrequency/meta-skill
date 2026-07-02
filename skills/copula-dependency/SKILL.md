---
name: copula-dependency
version: 0.1.0
description: Copula-based dependency modeling for joint risk and multivariate simulation. Use when you need to model dependence between assets *separately* from their marginal distributions — i.e., fit each return series' marginal distribution, then glue them together with a copula (Gaussian, Student-t, Frank, Clayton, Gumbel) for joint sampling. Best for portfolio VaR / CVaR where tail dependence matters and the Gaussian assumption fails. Uses the sdv-dev/Copulas library. NOT for single-asset modeling, simple Gaussian linear correlation sufficiency, or pure tail-dependence asymptotics — use EVT or parametric marginals directly instead.
allowed-tools: Bash, Read, Edit, Write
license: BUSL-1.1 (sdv-dev/Copulas)
metadata:
    skill-author: HyperFrequency
---

# Copula-Based Dependency Modeling

## Overview

A copula is a function that couples univariate marginal distributions into a joint distribution. The key insight (Sklar's theorem): any joint distribution can be decomposed into marginals + a copula. This lets you fit each asset's marginal independently (allowing heavy tails, skew, anything) and then model the *dependence* with a separate copula object.

The `sdv-dev/Copulas` library (Python) supports:
- **Multivariate**: `GaussianMultivariate`, `VineCopula` (regular/center/direct vines)
- **Bivariate parametric**: `Gaussian`, `Frank`, `Clayton`, `Gumbel` — Archimedean families with different tail behaviors

This skill focuses on portfolio applications: fit a copula on two or more return series, then sample joint scenarios for risk simulation.

## When to Use This Skill

This skill should be used when:
- Modeling joint return distributions where Gaussian correlation under-represents tail co-movement
- Simulating multi-asset portfolio P&L for VaR / CVaR with non-Gaussian dependence
- Generating synthetic correlated return data for stress testing
- Combining heavy-tailed marginals (Student-t, skew-t) with a flexible dependence structure
- Decoupling marginal modeling (GARCH / EVT / KDE) from dependence modeling

Don't use this skill when:
- A linear correlation matrix is sufficient (Gaussian copula degenerates to multivariate normal)
- Only one asset is being modeled (no dependence to capture — use parametric marginals directly)
- You need tail-dependence asymptotics — Archimedean copulas have closed-form lower/upper tail dependence, but if asymptotic results are the *goal*, switch to EVT (extreme value theory) packages

## Install / Setup

```bash
pip install copulas
```

Verify:

```python
import copulas
from copulas.multivariate import GaussianMultivariate
print(copulas.__version__)  # 0.10.x+ as of 2025
```

`copulas` depends on `numpy`, `scipy`, `pandas`, `matplotlib`. Pure Python (no compiled extensions); installs cleanly on all platforms.

## Minimal Example — Fit Gaussian Copula on Two Return Series, Sample Joint Scenarios

```python
import numpy as np
import pandas as pd
from copulas.multivariate import GaussianMultivariate

# Two synthetic return series with non-trivial dependence and fat tails.
rng = np.random.default_rng(7)
n = 1_000
common = rng.standard_t(df=4, size=n)
asset_a = 0.7 * common + 0.3 * rng.standard_normal(n)
asset_b = 0.6 * common + 0.4 * rng.standard_t(df=5, size=n)
returns = pd.DataFrame({
    'asset_a': asset_a * 0.012,
    'asset_b': asset_b * 0.015,
})

# Fit a Gaussian copula. The library handles marginal fitting (KDE / parametric)
# internally and stores the copula correlation matrix separately.
copula = GaussianMultivariate()
copula.fit(returns)

# Sample 10,000 joint return scenarios.
synthetic = copula.sample(10_000)
print(synthetic.head())

# Joint 95% portfolio VaR (equal-weight).
portfolio_pnl = 0.5 * synthetic['asset_a'] + 0.5 * synthetic['asset_b']
var_95 = -np.quantile(portfolio_pnl, 0.05)
cvar_95 = -portfolio_pnl[portfolio_pnl <= np.quantile(portfolio_pnl, 0.05)].mean()
print(f"Joint 95% portfolio VaR:  {var_95:.4f}")
print(f"Joint 95% portfolio CVaR: {cvar_95:.4f}")

# Inspect the fitted copula correlation matrix and marginal types.
params = copula.to_dict()
print("Copula type:", params['type'])
print("Marginals:", [c['type'] for c in params['univariates']])
```

For bivariate Archimedean copulas (when you want explicit tail dependence):

```python
from copulas.bivariate import Clayton, Frank, Gumbel

# Clayton — lower tail dependence (joint crashes)
clayton = Clayton()
# Inputs must be rank-uniform on [0,1]; transform via empirical CDF first.
import scipy.stats as ss
u = ss.rankdata(returns['asset_a']) / (len(returns) + 1)
v = ss.rankdata(returns['asset_b']) / (len(returns) + 1)
clayton.fit(np.column_stack([u, v]))
print(f"Clayton theta: {clayton.theta:.3f}")  # higher theta = stronger lower-tail dep
```

## Key API Surface

| Object | Purpose |
|---|---|
| `copulas.multivariate.GaussianMultivariate` | Gaussian copula with auto-selected marginals |
| `copulas.multivariate.VineCopula(vine_type='regular')` | Vine copula for high-dim non-Gaussian dependence  // unverified — see https://sdv.dev/Copulas |
| `copula.fit(df)` | Fit marginals + copula structure from a DataFrame |
| `copula.sample(n)` | Generate `n` joint samples (returns DataFrame) |
| `copula.probability_density(X)` | Joint PDF at points `X` |
| `copula.cumulative_distribution(X)` | Joint CDF |
| `copula.to_dict()` / `from_dict(d)` | Serialize / deserialize fitted copula |
| `copula.save(path) / load(path)` | Persist to disk |
| `copulas.bivariate.Gaussian / Frank / Clayton / Gumbel` | Bivariate parametric copulas; require rank-uniform inputs |
| `bivariate.theta` | Fitted parameter (after `.fit()`); interpret per family |
| `copulas.visualization.compare_3d / scatter_2d` | Compare real vs synthetic |

## Interpreting the Output

**Marginal choice matters more than copula family at modest sample sizes.** With 500–2000 observations, the marginal fit drives the joint quantiles. The library auto-selects from KDE / Gaussian / Truncated-Gaussian / Gamma / Beta based on goodness-of-fit. Inspect `copula.to_dict()['univariates']` and override the marginal class via `parameters` if the auto-pick is wrong (e.g. force `GaussianKDE` for heavy-tailed series).

**Copula family characteristics:**
- **Gaussian** — symmetric, **no tail dependence** (asymptotically independent in extremes). Standard choice; matches multivariate-normal under Gaussian marginals.
- **Student-t copula** — symmetric, **strong tail dependence** in both tails. Not directly in `copulas` (see `pycop` or roll your own); preferred when joint crashes and joint rallies are both present.
- **Clayton** — asymmetric, **lower tail dependence only**. Captures "everything crashes together, rallies don't co-move." Common in credit / default modeling.
- **Gumbel** — asymmetric, **upper tail dependence only**. The mirror of Clayton.
- **Frank** — symmetric, **no tail dependence**. Like Gaussian but with a different functional form.

**Goodness of fit:** there is no single "fit statistic" for copulas in the library. Standard practice:
1. Sample 10x your data; compare empirical CDFs of marginals (KS test) and Spearman / Kendall correlation matrices.
2. Visual: 2D scatter `compare_2d(real, synthetic)`. The dependence structure should be qualitatively similar.
3. For Archimedean: compare fitted `theta` to the value implied by Kendall's tau — large discrepancy ⇒ wrong family.

**Theta interpretation (bivariate):**
- Clayton: `theta in (0, inf)`, larger = stronger lower-tail dep. Kendall's tau = theta / (theta + 2).
- Gumbel: `theta in [1, inf)`, larger = stronger upper-tail dep. tau = (theta - 1) / theta.
- Frank: `theta in (-inf, inf) \ {0}`, sign = direction of dependence.

## Workflow: GARCH + Copula for Joint Portfolio VaR

A canonical multivariate risk pipeline (sometimes called "Copula-GARCH"):

```python
import numpy as np
import pandas as pd
from arch import arch_model
from copulas.multivariate import GaussianMultivariate

# 1. Two return series (decimal). Fit univariate GARCH-t on each.
returns = pd.DataFrame({'a': ..., 'b': ...})  # daily decimal returns

std_resids = {}
forecasts = {}
for col in returns.columns:
    r_pct = returns[col] * 100  # arch wants percent
    res = arch_model(r_pct, mean='Constant', vol='GARCH', p=1, o=1, q=1, dist='t').fit(disp='off')
    std_resids[col] = res.std_resid                              # i.i.d.-ish under correct spec
    forecasts[col] = float(np.sqrt(res.forecast(horizon=1, reindex=False).variance.iloc[-1, 0]))

# 2. Fit a Gaussian copula on the standardized residuals (which are now i.i.d. across t).
resids_df = pd.DataFrame(std_resids).dropna()
copula = GaussianMultivariate()
copula.fit(resids_df)

# 3. Sample 50k joint scenarios in standardized-residual space.
syn = copula.sample(50_000)

# 4. Scale back to return space using next-day GARCH sigma forecasts.
sim_a = syn['a'] * forecasts['a'] / 100  # back to decimal
sim_b = syn['b'] * forecasts['b'] / 100

# 5. Equal-weight portfolio VaR / CVaR.
pnl = 0.5 * sim_a + 0.5 * sim_b
var_95 = -np.quantile(pnl, 0.05)
cvar_95 = -pnl[pnl <= np.quantile(pnl, 0.05)].mean()
print(f"GARCH-Copula 1-day 95% VaR:  {var_95:.4%}")
print(f"GARCH-Copula 1-day 95% CVaR: {cvar_95:.4%}")
```

This pipeline separates concerns cleanly: GARCH handles the time-varying conditional variance, the copula handles the dependence structure of the *standardized* residuals (which are approximately stationary), and Monte Carlo recombines them into joint scenarios.

## Common Pitfalls

1. **Forgetting to rank-transform for bivariate copulas.** `copulas.bivariate.*` expects inputs on `[0, 1]^2` (the copula domain). Passing raw returns gives garbage parameters. Always transform via `scipy.stats.rankdata(x) / (n + 1)` first. `GaussianMultivariate` (top-level) handles this internally; the bivariate classes do not.
2. **Treating Gaussian copula as equivalent to correlation.** Under Gaussian *marginals*, the Gaussian copula reduces to a correlation matrix. Under non-Gaussian marginals, the Gaussian copula's **correlation parameter is not equal to the linear (Pearson) correlation of returns** — it's the correlation of the inverse-Gaussian-CDF transformed series. Cross-check via Spearman rank correlation, which is invariant under monotone marginal transforms.
3. **Underestimating joint-tail risk with Gaussian copulas.** The Gaussian copula has zero tail dependence: extreme joint events are asymptotically independent. For portfolio VaR under crisis scenarios this systematically **underestimates** joint losses. Student-t or Clayton copulas are stress-test-honest. (This is the classic "Gaussian copula and the financial crisis" story; see Salmon, *Wired*, 2009.)
4. **Sample sizes too small for multivariate fits.** Vine copulas with `d` assets have `O(d^2)` pair-copulas; 1,000 obs and 10 assets is borderline. Fitting will succeed but the parameters are noisy. Either reduce dimension via PCA / clustering, or use a more parsimonious family.
5. **Confusing sampling with conditional sampling.** `copula.sample(n)` draws *unconditional* joint scenarios. For "what is asset B given asset A < -5%?", you need conditional sampling, which requires solving the conditional copula CDF — not exposed directly for all families. Often easier to rejection-sample: draw many, filter to the condition.
6. **Library version churn.** `sdv-dev/Copulas` is part of the SDV ecosystem and the API has shifted (e.g. `GaussianMultivariate.params` became `to_dict()`). Pin a version in `requirements.txt` and re-check on upgrades.

## References

### Primary library
- [sdv-dev/Copulas on GitHub](https://github.com/sdv-dev/Copulas) — upstream repo, issues, releases (v0.10+)
- [Copulas documentation](https://sdv.dev/Copulas/) — pinned to v0.10.x as of cross-check
- [GaussianMultivariate quickstart notebook](https://github.com/sdv-dev/Copulas/blob/main/tutorials/README%20Quickstart.ipynb) — the minimal `fit` / `sample` pipeline
- [Copulas tutorials directory](https://github.com/sdv-dev/Copulas/tree/main/tutorials) — bivariate/multivariate/vine notebooks
- [Copulas examples (synthetic data for ML)](https://github.com/sdv-dev/Copulas/blob/main/tutorials/04_Synthetic_Data_for_Machine_Learning.ipynb) — using copulas to augment training data

### Deep-dive docs (specific pages worth bookmarking)
- [`GaussianMultivariate` API](https://sdv.dev/Copulas/api/copulas.multivariate.gaussian.html) — `to_dict`, `from_dict`, `save`, `load`; serialization patterns
- [VineCopula API](https://sdv.dev/Copulas/api/copulas.multivariate.vine.html) — regular/center/direct vine specifications
- [Bivariate Archimedean copulas](https://github.com/sdv-dev/Copulas/tree/main/copulas/bivariate) — `Frank`, `Clayton`, `Gumbel`, `Gaussian`; the rank-uniform input contract
- [Visualization module](https://github.com/sdv-dev/Copulas/tree/main/copulas/visualization) — `compare_2d`, `compare_3d`, `scatter_2d` for real-vs-synthetic diagnostics
- [Univariate auto-selection](https://github.com/sdv-dev/Copulas/tree/main/copulas/univariate) — KDE / Gaussian / Truncated-Gaussian / Beta / Gamma fitting that `GaussianMultivariate.fit()` calls internally

### Adjacent / alternative libraries
- [pyvinecopulib](https://github.com/vinecopulib/pyvinecopulib) — Python bindings for vinecopulib (C++); the most actively-maintained vine implementation and a more performant alternative for high-d
- [statsmodels.distributions.copula](https://www.statsmodels.org/stable/distributions.html#copula) — `GaussianCopula`, `StudentTCopula`, `IndependenceCopula`; has the Student-t copula that sdv-dev Copulas lacks
- [pycop](https://github.com/maximenc/pycop) — bivariate copulas including Student-t with tail dependence; lightweight
- [scipy.stats.multivariate_t](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.multivariate_t.html) — when the joint distribution itself is multivariate Student-t (not just the copula)
- [POT (Python Optimal Transport)](https://pythonot.github.io/) — when you want optimal-transport distances between joint distributions instead of copula likelihoods

### Academic papers
- Sklar, A. (1959). "Fonctions de répartition à n dimensions et leurs marges." *Publications de l'Institut Statistique de l'Université de Paris* 8, 229-231. [SSRN translation](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4198458) — the original copula theorem; English translation by Van Vliet.
- Cherubini, U., Luciano, E., & Vecchiato, W. (2004). *Copula Methods in Finance*. Wiley. [DOI: 10.1002/9781118673331](https://doi.org/10.1002/9781118673331) ISBN 9780470863442 — the canonical finance-applied reference; pricing, risk, and credit.
- Nelsen, R. B. (2006). *An Introduction to Copulas* (2nd ed.). Springer. ISBN 9780387286594 — the math reference; Archimedean families, tail dependence, dependence concepts.
- Patton, A. J. (2006). "Modelling Asymmetric Exchange Rate Dependence." *International Economic Review* 47(2), 527-556. [DOI: 10.1111/j.1468-2354.2006.00387.x](https://doi.org/10.1111/j.1468-2354.2006.00387.x) — the canonical conditional-copula time-series paper; introduces SJC copula.
- Patton, A. J. (2012). "A Review of Copula Models for Economic Time Series." *Journal of Multivariate Analysis* 110, 4-18. [DOI: 10.1016/j.jmva.2012.02.021](https://doi.org/10.1016/j.jmva.2012.02.021) — survey of dynamic copulas, estimation methods, goodness-of-fit tests for time-series applications.
- McNeil, A. J., Frey, R., & Embrechts, P. (2015). *Quantitative Risk Management: Concepts, Techniques and Tools* (revised ed.). Princeton. ISBN 9780691166278 — Chapter 7 on copulas; the operational reference for portfolio applications.
- Salmon, F. (2009). "Recipe for Disaster: The Formula That Killed Wall Street." *Wired* — the popular account of the Gaussian-copula failure in CDO pricing; useful pedagogical reference for tail-dependence risk.

### Tutorials & write-ups
- [Vinecopulib documentation](https://vinecopulib.github.io/pyvinecopulib/) — the cleanest exposition of vine copulas in Python; complements the sdv-dev tutorial
- [Patton's lecture notes on copulas](https://public.econ.duke.edu/~ap172/) — Duke Econ course materials; bibliography is the easiest entry to the academic literature
- [Copulas examples notebook (vine)](https://github.com/sdv-dev/Copulas/blob/main/tutorials/03_Vine_Copulas.ipynb) — when to choose regular vs center vs direct vines

### Standard datasets / benchmarks
- [Trivariate XYZ dataset](https://github.com/sdv-dev/Copulas/blob/main/copulas/datasets.py) — `from copulas.datasets import sample_trivariate_xyz`; the canonical sanity-check dataset shipped with the library
- 2-asset GARCH-Copula residual benchmark — fit GARCH on S&P 500 / Treasury daily returns, fit copula on standardized residuals; reproduces the canonical Patton (2012) figures

### Last cross-checked
2026-05-20 — via Context7 `/sdv-dev/copulas` (43 snippets, High reputation) + WebSearch verification of all paper DOIs.
