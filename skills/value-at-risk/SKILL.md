---
name: value-at-risk
description: Value-at-Risk (VaR) and Conditional VaR / Expected Shortfall (CVaR / ES) estimation on a returns series. Use when you need a single-number tail-risk summary at a stated confidence level (95%, 99%). Covers historical, parametric (Gaussian / t), and Monte Carlo VaR via quantstats and pyfolio. For GARCH-conditional VaR see garch-volatility; for joint-portfolio VaR via dependence structure see copula-dependency; for path-based scenario VaR see monte-carlo-simulation.
allowed-tools: Bash, Read, Edit, Write
license: Apache-2.0 (quantstats); Apache-2.0 (pyfolio)
metadata:
    skill-author: HyperFrequency
---

# Value-at-Risk and Expected Shortfall

## Overview

**VaR** at confidence level `c` is the loss that is exceeded with probability `1-c` over a stated horizon. Daily 95% VaR of 2% means: "on a typical day, we expect to lose more than 2% one day in twenty." **CVaR** (also called Expected Shortfall, ES) is the *average* loss given that VaR is exceeded — a coherent risk measure (VaR is not coherent: it fails subadditivity in pathological cases).

This skill uses `quantstats` (canonical Python API for VaR/CVaR on a returns series) and `pyfolio` / `pyfolio-reloaded` (broader risk tearsheets). Both consume a `pd.Series` of returns indexed by date.

## When to Use This Skill

This skill should be used when:
- Reporting a single-number tail-risk metric on a daily return series
- Comparing risk across strategies or assets at standard confidence levels (95%, 99%)
- Backtesting VaR estimates against realized exceedances (hit-rate / Kupiec test)
- Producing a tearsheet section that documents downside risk
- Quickly choosing between historical, parametric, and Monte Carlo VaR

Don't use these libraries when:
- The risk has explicit conditional structure (use `garch-volatility` to get sigma_t, then scale parametric VaR)
- The portfolio has many assets with non-trivial joint tail dependence (use `copula-dependency` + Monte Carlo)
- You need regulatory-grade VaR (Basel) — use the bank's internal model; this skill is for research / strategy analysis

## Install / Setup

```bash
pip install quantstats
# pyfolio is dormant; the community-maintained fork is preferred:
pip install pyfolio-reloaded
```

Both expect returns as a `pd.Series` of decimals (e.g. `0.012` for 1.2%), DatetimeIndex preferred.

## Minimal Example — VaR & CVaR via quantstats

```python
import numpy as np
import pandas as pd
import quantstats as qs

# Synthetic 3-year daily return series, with fatter left tail than Normal.
rng = np.random.default_rng(11)
returns = pd.Series(
    rng.standard_t(df=5, size=252 * 3) * 0.011 + 0.0003,
    index=pd.date_range('2022-01-03', periods=252 * 3, freq='B'),
    name='strategy',
)

# Historical VaR / CVaR — empirical quantile of returns.
# quantstats convention: `confidence` is the confidence level (0.95 = 95%).
# Returned value is the (signed, negative-for-losses) return at that quantile.
var_95  = qs.stats.var(returns, confidence=0.95)
cvar_95 = qs.stats.cvar(returns, confidence=0.95)
print(f"Historical 95% 1-day VaR:  {var_95:.4%}")
print(f"Historical 95% 1-day CVaR: {cvar_95:.4%}")

# Parametric (Gaussian) VaR — quick sanity check.
mu, sigma = returns.mean(), returns.std()
from scipy.stats import norm
param_var_95 = mu + sigma * norm.ppf(1 - 0.95)
print(f"Parametric Gaussian 95% VaR: {param_var_95:.4%}")

# Backtest hit rate — fraction of days where realized loss exceeds the VaR threshold.
# For an honest 95% VaR, hit rate should be ~5%.
hits = (returns < var_95).mean()
print(f"Realized hit rate at 95% VaR: {hits:.2%}  (target ~5%)")

# Full HTML tearsheet (drops a file with VaR, drawdowns, rolling Sharpe, etc.):
# qs.reports.html(returns, output='strategy_report.html')
```

For pyfolio:

```python
import pyfolio as pf  # or `import pyfolio_reloaded as pf`
# Single tail-risk number via pyfolio.timeseries.value_at_risk:
pf_var = pf.timeseries.value_at_risk(returns, period=None, sigma=2.0)  # 2-sigma ~ 97.7%
# Full returns tearsheet (in a notebook): pf.create_returns_tear_sheet(returns)
```

## Key API Surface

| Function | Purpose |
|---|---|
| `qs.stats.var(returns, confidence=0.95)` | Historical VaR (empirical quantile) |
| `qs.stats.cvar(returns, confidence=0.95)` | Conditional VaR / Expected Shortfall |
| `qs.stats.expected_shortfall(returns, confidence=0.95)` | Alias for `cvar` |
| `qs.stats.tail_ratio(returns, cutoff=0.95)` | Ratio of right-tail to left-tail magnitude |
| `qs.stats.risk_of_ruin(returns)` | Probability of total capital loss given current edge / vol |
| `qs.reports.html(returns, output=...)` | Full HTML tearsheet including VaR table |
| `qs.reports.metrics(returns)` | Printable metrics table including 95% & 99% VaR |
| `pf.timeseries.value_at_risk(returns, period, sigma)` | Sigma-based (parametric) VaR  // unverified — see https://github.com/quantopian/pyfolio |
| `pf.create_returns_tear_sheet(returns)` | Returns tearsheet with drawdown + VaR table |

## Interpreting the Output

**Sign convention.** `qs.stats.var` and `cvar` return *signed* return values — a 95% VaR of `-0.021` means "5% of days lose more than 2.1%." Some shops report VaR as a positive number (`0.021` = "21 cents of loss per dollar"); convert when communicating externally.

**Backtest hit rate (Kupiec test).** Realized exceedances should occur at frequency `1 - c`. If you set `c = 0.95` and observe 12% hit rate over a year (≈ 30 exceedances on 252 days), your VaR is **too tight** and the model is mis-specified. If you observe 1%, the VaR is **too loose** (over-conservative). A rough rule:
- Expected exceedances in `T` days: `T * (1 - c)`
- Acceptable range (Kupiec 95% confidence) for `T=252, c=0.95`: roughly `6–22` exceedances

**Historical vs. parametric vs. Monte Carlo.**
- **Historical** — quantile of realized returns. No distribution assumption. Captures fat tails *if they exist in your sample*; useless for unprecedented shocks.
- **Parametric Gaussian** — `mu + sigma * z_{1-c}`. Closed-form, fast, but **systematically underestimates** tail risk on most financial series because returns have kurtosis > 3.
- **Parametric Student-t** — fits `nu` (degrees of freedom) to the empirical kurtosis. Heavier tails than Gaussian; usually 2x-3x more accurate at 99%.
- **Monte Carlo** — simulate paths under a stochastic model (GBM, GARCH, copula). Most flexible, most computationally expensive, results depend on model assumptions.

A robust workflow reports all three: large discrepancies signal model risk.

**CVaR > VaR always.** CVaR is the *average* loss in the tail; VaR is the *threshold*. By construction CVaR ≥ VaR in magnitude. If your CVaR is barely larger than VaR, the tail is thin (or you have too few tail observations).

## Three VaR Estimators Side-by-Side

For the same data, the three approaches often disagree. Reporting all three is good practice; large disagreement signals model risk.

```python
import numpy as np
import pandas as pd
from scipy.stats import norm, t as student_t

returns = pd.Series(...)  # your daily decimal returns
c = 0.95
alpha = 1 - c

# 1. Historical — empirical quantile
hist_var = np.quantile(returns, alpha)

# 2. Parametric Gaussian
mu, sigma = returns.mean(), returns.std()
param_gauss_var = mu + sigma * norm.ppf(alpha)

# 3. Parametric Student-t (fit df by MLE)
nu, loc, scale = student_t.fit(returns)
param_t_var = student_t.ppf(alpha, df=nu, loc=loc, scale=scale)

# 4. Monte Carlo VaR via bootstrap (1-day): degenerate to historical for h=1,
#    but useful for multi-day; see monte-carlo-simulation skill.

print(pd.Series({
    'historical': hist_var,
    'parametric_gauss': param_gauss_var,
    'parametric_t': param_t_var,
}).map(lambda x: f"{x:.4%}"))
```

If the parametric-t VaR is materially more negative than the parametric-Gaussian VaR, the series has heavy tails (low fitted `nu`, typically 3-6 for equities). The Gaussian estimate is then **wrong** and the t estimate is closer to the true tail risk.

## Kupiec Hit-Rate Backtest (Sketch)

```python
import numpy as np
from scipy import stats as ss

# Walk-forward: at each t, fit VaR on data[:t], record whether realized return[t]
# breaches the VaR estimate.
def kupiec_pof(n_exceedances, n_obs, c):
    """Kupiec's proportion-of-failures (POF) likelihood-ratio test."""
    p = 1 - c
    if n_exceedances == 0:
        return 0.0, 1.0
    lr = -2 * np.log(
        ((1 - p)**(n_obs - n_exceedances) * p**n_exceedances) /
        ((1 - n_exceedances/n_obs)**(n_obs - n_exceedances) * (n_exceedances/n_obs)**n_exceedances)
    )
    pval = 1 - ss.chi2.cdf(lr, df=1)
    return lr, pval

# Example: 252 days, 95% VaR, observed 18 exceedances vs expected ~13.
lr, pval = kupiec_pof(n_exceedances=18, n_obs=252, c=0.95)
print(f"Kupiec LR: {lr:.2f}, p-value: {pval:.3f}")
# p > 0.05 means we can't reject "model is well-calibrated".
```

A pass on Kupiec is necessary but not sufficient: it ignores **clustering** of exceedances (you can fail by having all 13 in one week). For a fuller backtest, also run Christoffersen's conditional coverage test (combined POF + independence of exceedances).

## Common Pitfalls

1. **Returns scale mismatch.** `quantstats` expects decimals (`0.012` for 1.2%). Passing percent (`1.2`) gives VaR estimates 100x too large. Symptom: 95% VaR reported as `-1.6` (160% daily loss).
2. **Historical VaR on small samples.** Estimating 99% VaR from 252 daily returns uses ~2.5 tail observations. The estimate has huge sampling error. Either use parametric / MC, or extend the sample (5+ years).
3. **Confusing horizon.** `qs.stats.var` returns **1-period** VaR (1 day if your series is daily). Scaling to 10-day VaR via `sqrt(10)` assumes IID Gaussian — wrong for fat-tailed / serially correlated returns. For longer horizons, simulate paths (`monte-carlo-simulation`) or refit on weekly / monthly returns.
4. **Backtesting without out-of-sample.** Computing VaR on the same window you measure exceedances on is **in-sample by construction**: the hit rate will mechanically match the confidence level. Always backtest on a window the VaR model didn't see.
5. **Treating VaR as a worst case.** It isn't. 95% VaR is exceeded **1 day in 20** — about 13 times a year on daily data. Communicating it as "the worst-case loss" is a common and dangerous mistake; use CVaR or stress tests for that framing.
6. **Pyfolio installation friction.** Original `pyfolio` (quantopian) is unmaintained and may break on modern pandas / numpy. Use `pip install pyfolio-reloaded` (community fork) for current-stack compatibility; the API is mostly identical.

## References

### Primary library
- [quantstats on GitHub](https://github.com/ranaroussi/quantstats) — upstream repo, issues, releases
- [quantstats README & quickstart](https://github.com/ranaroussi/quantstats#quantstats-portfolio-analytics-for-quants) — pinned to the current main branch
- [pyfolio (archive, Quantopian)](https://github.com/quantopian/pyfolio) — dormant but still cited; consult the source for legacy code
- [pyfolio-reloaded (active fork)](https://github.com/stefan-jansen/pyfolio-reloaded) — Stefan Jansen's maintained version, pandas/numpy compatible
- [empyrical-reloaded](https://github.com/stefan-jansen/empyrical-reloaded) — the raw metric implementations both quantstats and pyfolio sit on top of

### Deep-dive docs (specific pages worth bookmarking)
- [quantstats stats module source](https://github.com/ranaroussi/quantstats/blob/main/quantstats/stats.py) — `var`, `cvar`, `expected_shortfall`, `tail_ratio`, `risk_of_ruin` definitions inline; faster to read than docs
- [quantstats reports module](https://github.com/ranaroussi/quantstats/blob/main/quantstats/reports.py) — `html`, `full`, `metrics` reports; what each tearsheet section computes
- [pyfolio `timeseries.value_at_risk`](https://github.com/stefan-jansen/pyfolio-reloaded/blob/main/src/pyfolio/timeseries.py) — sigma-based parametric VaR implementation
- [pyfolio returns tear sheet API](https://github.com/stefan-jansen/pyfolio-reloaded/blob/main/src/pyfolio/tears.py) — full risk-section composition
- [scipy.stats.t](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.t.html) — used for parametric Student-t VaR; `t.ppf(alpha, df)` is the canonical call
- [arch bootstrap module](https://arch.readthedocs.io/en/latest/bootstrap/index.html) — for block-bootstrap VaR confidence intervals

### Adjacent / alternative libraries
- [riskfolio-lib](https://github.com/dcajasn/Riskfolio-Lib) — multi-asset CVaR, EVaR, drawdown-at-risk; production portfolio optimization with these as constraints
- [pyextremes](https://github.com/georgebv/pyextremes) — extreme-value theory (GPD, GEV) for tail VaR beyond the empirical sample
- [empyrical (Quantopian)](https://github.com/quantopian/empyrical) — original metric library; pyfolio-reloaded is the maintained fork
- [QuantLib-Python VaR examples](https://github.com/lballabio/QuantLib-SWIG/tree/master/Python) — Monte Carlo VaR for derivative portfolios
- [scipy.stats.genextreme / genpareto](https://docs.scipy.org/doc/scipy/reference/stats.html) — fitting GEV / GPD to tail exceedances for parametric extreme VaR

### Academic papers
- Acerbi, C., & Tasche, D. (2002). "On the coherence of Expected Shortfall." *Journal of Banking & Finance* 26(7), 1487-1503. [DOI: 10.1016/S0378-4266(02)00283-2](https://doi.org/10.1016/S0378-4266(02)00283-2) — why CVaR is a coherent risk measure and VaR is not.
- Christoffersen, P. F. (1998). "Evaluating Interval Forecasts." *International Economic Review* 39(4), 841-862. [JSTOR 2527341](https://www.jstor.org/stable/2527341) — the conditional coverage test pair (POF + independence) for VaR backtesting.
- Kupiec, P. H. (1995). "Techniques for Verifying the Accuracy of Risk Measurement Models." *Journal of Derivatives* 3(2), 73-84. [DOI: 10.3905/jod.1995.407942](https://doi.org/10.3905/jod.1995.407942) — the proportion-of-failures (POF) likelihood-ratio test implemented above.
- Jorion, P. (2007). *Value at Risk: The New Benchmark for Managing Financial Risk* (3rd ed.). McGraw-Hill. ISBN 9780071464956 — the standard practitioner reference.
- McNeil, A. J., Frey, R., & Embrechts, P. (2015). *Quantitative Risk Management: Concepts, Techniques and Tools* (revised ed.). Princeton. ISBN 9780691166278 — Chapters 2 and 7 cover VaR, ES, and EVT in operational detail.
- Lo, A. W. (2002). "The Statistics of Sharpe Ratios." *Financial Analysts Journal* 58(4), 36-52. [DOI: 10.2469/faj.v58.n4.2453](https://doi.org/10.2469/faj.v58.n4.2453) — the sampling distribution that feeds parametric VaR confidence intervals.

### Tutorials & write-ups
- [quantstats README walkthrough](https://github.com/ranaroussi/quantstats#using-quantstats) — covers the full VaR / CVaR / tearsheet pipeline on real returns
- [pyfolio-reloaded notebooks](https://github.com/stefan-jansen/pyfolio-reloaded/tree/main/examples) — full-tearsheet examples with risk sections
- [Christoffersen test implementation reference](https://www.mathworks.com/help/risk/varbacktest.cci.html) — MATLAB doc explaining the conditional-coverage chi-squared statistic

### Standard datasets / benchmarks
- Synthetic Student-t returns with df=5, scale=0.012 — the standard "fat-tailed but reproducible" VaR sandbox used above
- S&P 500 daily returns 2000-2024 via `yfinance` — runs through Kupiec / Christoffersen tests; the 2008 and 2020 windows are the canonical regime stress tests
- Christoffersen-Pelletier (2004) Markov-jump VaR DGPs — for adversarial backtesting

### Last cross-checked
2026-05-20 — via Context7 `/ranaroussi/quantstats` (126 snippets, High, benchmark 95.7) + `/quantopian/pyfolio` (36 snippets, High) + WebSearch verification of all paper DOIs.
