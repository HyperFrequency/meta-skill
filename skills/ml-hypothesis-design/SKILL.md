---
name: ml-hypothesis-design
description: Design testable ML hypotheses for quant strategies with statistical rigor. Use when formulating null vs alternative hypotheses for trading signals, computing required statistical power before research, applying multiple-testing corrections (Bonferroni, FDR, Deflated Sharpe Ratio), or preregistering a research plan. Triggers on phrases like "is this signal real", "how many backtests can I run", "deflate this Sharpe", "preregister this study", "what's the null", "minimum backtest length", or "how do I avoid p-hacking". For exploratory ideation use scientific-brainstorming; for general hypothesis formulation use hypothesis-generation; for evaluating models after the fact use model-evaluation.
allowed-tools: Read Write Edit Bash
---

# ML Hypothesis Design for Quant Strategies

## Overview

Quant ML research has a hard adversary that bench science doesn't: **the data is public, the search space is enormous, and a researcher who tries 1,000 strategies will find a "significant" one by chance alone**. The field is littered with backtests that passed every conventional test but failed live.

This skill is the discipline that prevents that. It treats every trading signal as a hypothesis that must be specified *before* you look at the result, with a null model, a power calculation, and a multiple-testing budget. It refuses to let a researcher quote a raw Sharpe ratio without saying how many trials it survived.

## When to Use This Skill

Use this skill when:

- About to launch a new research program and need to define what "this works" means before running a backtest
- Comparing N candidate strategies and need to decide which (if any) cleared a multiple-testing corrected threshold
- Reporting a strategy's performance and need to deflate its Sharpe for selection bias
- Deciding how long a backtest must run to detect a target Sharpe at desired power
- Writing a preregistration document or research log entry
- Reviewing someone else's claim that a strategy "worked"

Do **not** use this for: exploratory data analysis where you have no prior hypothesis (use `scientific-brainstorming` first), or pure model evaluation after a hypothesis is already specified (use `model-evaluation`).

## Core Framework

### Step 1 — State the hypothesis as a falsifiable claim

Every quant hypothesis must have these four components, written down *before* the backtest runs:

1. **Population / universe.** Which instruments, what frequency, what date range? "S&P 500 constituents as of 2010-01-01, daily close-to-close, 2010-2020 in-sample, 2020-2024 out-of-sample."
2. **Signal definition.** Exactly how the feature is computed. Pseudocode, not English. If you can't write the code without the data in front of you, the hypothesis isn't specified.
3. **Null model H0.** What does "this signal doesn't work" look like? The most common nulls: (a) Sharpe = 0 after costs, (b) Sharpe equals the benchmark (e.g. SPY buy-and-hold), (c) returns are indistinguishable from a random-sign permutation of the same feature.
4. **Alternative H1.** A specific effect size you'd commit to detecting. Not "this strategy works" but "annualized Sharpe ≥ 0.8 net of 5 bps round-trip cost". Without a target effect size you cannot compute power.

**Decision rule.** State what result will make you abandon the hypothesis. If your decision rule is "ship if profitable", you have no hypothesis — you have a wish.

### Step 2 — Compute statistical power before running the backtest

The Sharpe ratio has a known sampling distribution. The standard error under the null SR = 0 is approximately:

```
SE(SR) ≈ sqrt((1 + 0.5 * SR^2) / N)
```

where `N` is the number of observations (e.g. trading days). For a normal-returns approximation (Lo, 2002), to detect a Sharpe of 0.8 at 80% power and 5% significance you need roughly `N ≥ ((z_α + z_β) / SR_target)^2 ≈ (1.65 + 0.84)^2 / 0.64 ≈ 9.7` years of daily data — and that is the *power requirement under the null*, not the trial-adjusted requirement.

**Minimum Backtest Length (MinBTL)** from Bailey & Lopez de Prado (2014) generalizes this for `N_trials` candidate strategies. The intuition: if you tried more strategies, you need a longer backtest for the best one to be credible.

### Step 3 — Budget for multiple testing *before* you start

If you will examine `N` candidate strategies, fix the multiple-testing correction in advance:

- **Bonferroni** (controls family-wise error at level α): require each test's p-value < α / N. Conservative; suitable when N is small and false positives are catastrophic.
- **Benjamini-Hochberg FDR** (controls false discovery rate at q): less conservative, suitable for screening when you expect a few real signals among many.
- **Deflated Sharpe Ratio** (Bailey & Lopez de Prado 2014): adjusts the observed Sharpe for the number of trials, the variance across those trials, the skewness and kurtosis of returns, and the sample length. This is the strongest correction for quant research and is what should be reported.

The non-negotiable rule: **the trial count `N` includes every variant you considered, not just the one you're reporting.** Hyperparameter sweeps count. Universe variants count. Failed experiments count.

### Step 4 — Preregister

Write down — in a timestamped artifact (a markdown file in version control, an Obsidian note with a date stamp, anything immutable) — the entire plan before you have a result:

- The four hypothesis components from Step 1
- The N_trials budget and chosen correction
- The exact metric being optimized (e.g. "out-of-sample Sharpe over 2020-2024")
- The decision rule for ship/no-ship
- Any data transformations and the order they will be applied
- The walk-forward / cross-validation scheme (delegate detail to `model-evaluation`)

After the result is in, write the diff: what you actually did vs the preregistration, and why.

### Step 5 — Report deflated metrics, not raw

When publishing a result, the reported headline metric is the Deflated Sharpe and the probability of overfitting (PBO), not the raw Sharpe. Raw metrics go in an appendix.

## Code Snippets

### Deflated Sharpe Ratio

The Deflated Sharpe Ratio (DSR) computes the probability that the *observed* Sharpe ratio exceeds the maximum Sharpe expected under the null, given `N_trials` candidates and the higher moments of returns.

```python
import numpy as np
from scipy.stats import norm
from scipy.special import erfinv


def expected_max_sharpe(n_trials: int, sharpe_std: float = 1.0) -> float:
    """Expected maximum Sharpe across n_trials i.i.d. candidates with std sharpe_std.

    Uses the Gumbel/extreme-value approximation from Bailey & Lopez de Prado (2014).
    sharpe_std is the cross-trial std of Sharpe ratios under the null.
    """
    if n_trials < 2:
        return 0.0
    euler_mascheroni = 0.5772156649
    # E[max] ≈ sqrt(2 * ln(N)) - (gamma + ln(ln(N))) / (2 * sqrt(2 * ln(N)))
    # Wait — Bailey's form is:
    z = (1 - euler_mascheroni) * norm.ppf(1 - 1.0 / n_trials) \
        + euler_mascheroni * norm.ppf(1 - 1.0 / (n_trials * np.e))
    return sharpe_std * z


def deflated_sharpe_ratio(
    observed_sr: float,
    n_obs: int,
    skewness: float,
    kurtosis: float,
    n_trials: int,
    sharpe_std: float = 1.0,
) -> float:
    """Deflated Sharpe Ratio: probability the strategy's true Sharpe > 0
    given n_trials candidates and non-normal returns.

    Returns a probability in [0, 1]. A DSR > 0.95 is the conventional ship threshold.

    Reference: Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio",
    Journal of Portfolio Management 40(5), 94-107.
    """
    # Expected max Sharpe under the null with n_trials candidates
    sr_null = expected_max_sharpe(n_trials, sharpe_std)

    # Variance of the Sharpe estimator (Mertens 2002; accounts for skew/kurt)
    sr_var = (1 - skewness * observed_sr + ((kurtosis - 1) / 4) * observed_sr ** 2) / (n_obs - 1)
    sr_se = np.sqrt(sr_var)

    # DSR is the probability the observed exceeds the null max
    return float(norm.cdf((observed_sr - sr_null) / sr_se))


# Example
dsr = deflated_sharpe_ratio(
    observed_sr=1.2,       # Annualized Sharpe from your best backtest
    n_obs=252 * 5,         # 5 years of daily returns
    skewness=-0.3,         # Sample skewness of returns
    kurtosis=4.0,          # Sample kurtosis (NOT excess)
    n_trials=100,          # How many strategies you tried
    sharpe_std=0.5,        # Cross-trial Sharpe std (estimate from your sweep)
)
print(f"Deflated Sharpe (probability true SR > 0): {dsr:.3f}")
```

### Minimum Backtest Length

```python
def minimum_backtest_length(sharpe_target: float, n_trials: int, freq: int = 252) -> float:
    """Years of backtest needed so the best-of-N strategy's Sharpe is credible.

    Reference: Bailey, Borwein, Lopez de Prado, Zhu (2014/2017), "The Probability
    of Backtest Overfitting". Approximation: MinBTL ≈ (E[max SR under H0] / SR_target)^2.
    """
    sr_max_null = expected_max_sharpe(n_trials, sharpe_std=1.0)
    years = (sr_max_null / sharpe_target) ** 2
    return years


print(f"Minimum backtest length for SR=1.0 with 50 trials: "
      f"{minimum_backtest_length(1.0, 50):.1f} years")
# ~5.3 years — if you only have 3 years of data, the best of 50 trials is not credible.
```

### Bonferroni for a strategy sweep

```python
from scipy.stats import norm


def sharpe_pvalue(sr: float, n_obs: int) -> float:
    """One-sided p-value for H0: Sharpe = 0 (normal returns approximation, Lo 2002)."""
    se = np.sqrt((1 + 0.5 * sr ** 2) / n_obs)
    z = sr / se
    return 1 - norm.cdf(z)


def bonferroni_survivors(sharpes: list[float], n_obs: int, alpha: float = 0.05) -> list[int]:
    """Return indices of strategies that survive Bonferroni at family-wise alpha."""
    threshold = alpha / len(sharpes)
    return [i for i, sr in enumerate(sharpes) if sharpe_pvalue(sr, n_obs) < threshold]
```

## Common Pitfalls

1. **Counting only the "final" strategy in the trial budget.** Every hyperparameter you tuned, every universe you tested, every alternative spec — they all count. If you don't know N, assume the worst case.
2. **Selecting in-sample, evaluating in-sample.** If you used 2010-2020 to pick the best variant, the 2010-2020 Sharpe is meaningless. You need a truly held-out period (see `model-evaluation` for purged + embargoed CV).
3. **Quoting raw Sharpe in the abstract, deflated Sharpe in the appendix.** This is backwards. The headline number is the corrected one. If you can't say it with a deflated metric, you don't have a result.
4. **Assuming Gaussian returns when computing significance.** Returns have skew and excess kurtosis; this inflates the standard error of the Sharpe. Use the Mertens (2002) correction (included in the DSR snippet).
5. **Treating "passes preregistration" as "is real".** Preregistration prevents the worst form of cherry-picking, but doesn't guarantee causal validity, robustness to regime change, or that the signal will survive in live trading. It's necessary, not sufficient.
6. **Hypothesizing after the result is known (HARKing).** If you see a pattern in the data and then write a hypothesis to "test" it on the same data, you have circular reasoning. Either get fresh data, or commit and run.

## Tooling References

This skill defines methodology. Operationalize it with:

- **`scikit-learn`** skill — for the underlying model fitting; pair with this skill's preregistration step.
- **`model-evaluation`** skill (sister skill) — for purged/embargoed CV, walk-forward, and PBO computation.
- **`feature-engineering`** skill (sister skill) — for leakage-safe feature pipelines that don't undermine your hypothesis.
- **`vectorbt`** skill — for running the backtest sweep that produces the `n_trials` number you'll deflate against.
- **`tearsheet-generator`** skill — for the final report; include both raw and deflated metrics.
- **`quant-analyst`** skill — for higher-level workflow when this is one phase of a larger research project.

## References

### Primary library
This skill is methodology-first; the operational backbone is `mlfinlab` (the reference implementation of Lopez de Prado's algorithms) plus `scipy.stats` for power calculations and `statsmodels.stats.multitest` for multiple-testing corrections.

- [mlfinlab on GitHub](https://github.com/hudson-and-thames/mlfinlab) — Hudson & Thames implementation of Lopez de Prado's AFML algorithms; includes `BacktestStatistics` (deflated Sharpe), PBO, CSCV
- [mlfinlab documentation](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/) — pinned to v1.x
- [scipy.stats](https://docs.scipy.org/doc/scipy/reference/stats.html) — `norm`, `t`, `chi2`, `binom_test` for the underlying power calculations
- [statsmodels.stats.multitest](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) — `multipletests` for Bonferroni / Holm / FDR-BH corrections

### Deep-dive docs (specific pages worth bookmarking)
- [mlfinlab `BacktestStatistics`](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/backtest_statistics/backtest_statistics.html) — operational deflated Sharpe + probabilistic Sharpe; the snippets in this skill mirror this API
- [mlfinlab CSCV / PBO module](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/cross_validation/combinatorial_purged_cv.html) — combinatorial purged CV that feeds PBO
- [statsmodels `power` module](https://www.statsmodels.org/stable/stats.html#power-and-sample-size-calculations) — `tt_solve_power`, `zt_ind_solve_power` for sample-size requirements before the experiment
- [scipy.special.erfinv](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.erfinv.html) — used in the extreme-value approximation for `expected_max_sharpe`
- [statsmodels `multipletests`](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) — Bonferroni, Holm, BH-FDR, BY-FDR; pick by your false-discovery budget

### Adjacent / alternative libraries
- [arch.bootstrap.SPA](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html) — Hansen's Superior Predictive Ability test; the statistically formal alternative to "best Sharpe of N"
- [arch.bootstrap.MCS](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html) — Model Confidence Set (Hansen, Lunde, Nason 2011); pick the set of strategies indistinguishable from the best
- [pingouin](https://pingouin-stats.org/) — friendlier wrapper around scipy/statsmodels for power, effect-size, and multiple-comparisons; good for write-ups
- [riskfolio-lib](https://github.com/dcajasn/Riskfolio-Lib) — when the trial-budget question concerns portfolio weights instead of feature/model variants

### Academic papers
- Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality." *Journal of Portfolio Management* 40(5), 94-107. [SSRN 2460551](https://papers.ssrn.com/abstract=2460551) — the DSR; the headline metric this skill enforces.
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2014). "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance." *Notices of the AMS* 61(5), 458-471. [SSRN 2326253](https://papers.ssrn.com/abstract=2326253) — the polemic companion; the most readable statement of the problem.
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). "The Probability of Backtest Overfitting." *Journal of Computational Finance* 20(4), 39-69. [escholarship.org/uc/item/4w1110bb](https://escholarship.org/uc/item/4w1110bb) — formal PBO derivation.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. ISBN 9781119482086. Chapters 11-14 — backtest overfitting, deflated Sharpe, PBO operationalized.
- Lo, A. W. (2002). "The Statistics of Sharpe Ratios." *Financial Analysts Journal* 58(4), 36-52. [DOI: 10.2469/faj.v58.n4.2453](https://doi.org/10.2469/faj.v58.n4.2453) — the IID Sharpe-ratio sampling distribution; the power-calculation foundation.
- Mertens, E. (2002). "Comments on Variance of the IID estimator in Lo (2002)." Working paper — the skew/kurt correction used in the DSR variance estimator.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). "...and the Cross-Section of Expected Returns." *Review of Financial Studies* 29(1), 5-68. [DOI: 10.1093/rfs/hhv059](https://doi.org/10.1093/rfs/hhv059) — multiple-testing applied to the asset-pricing factor zoo; the t-statistic-must-exceed-3 result.
- Bailey, D. H., & López de Prado, M. (2014). "The Sharpe Ratio Efficient Frontier." *Journal of Risk* 15(2), 3-44. [SSRN 1821643](https://papers.ssrn.com/abstract=1821643) — probabilistic Sharpe ratio (PSR) under non-normal returns; complements DSR.
- Benjamini, Y., & Hochberg, Y. (1995). "Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing." *JRSS B* 57(1), 289-300. [JSTOR 2346101](https://www.jstor.org/stable/2346101) — the FDR procedure used as alternative to Bonferroni.
- Romano, J. P., & Wolf, M. (2005). "Stepwise Multiple Testing as Formalized Data Snooping." *Econometrica* 73(4), 1237-1282. [DOI: 10.1111/j.1468-0262.2005.00615.x](https://doi.org/10.1111/j.1468-0262.2005.00615.x) — bootstrap-based multiple-testing alternative to Bonferroni; powerful when test statistics are correlated.
- Hansen, P. R., Lunde, A., & Nason, J. M. (2011). "The Model Confidence Set." *Econometrica* 79(2), 453-497. [DOI: 10.3982/ECTA5771](https://doi.org/10.3982/ECTA5771) — set-of-best-strategies alternative to ranking and Bonferroni-correcting.

### Tutorials & write-ups
- [QuantConnect "Probabilistic Sharpe Ratio" research notebook](https://www.quantconnect.com/research/17112/probabilistic-sharpe-ratio/) — interactive walkthrough of PSR / DSR on real strategies
- [Hudson & Thames "Backtest Overfitting" series](https://hudsonthames.org/articles/) — practical PBO + DSR write-ups with code
- [Marcos Lopez de Prado lectures (Cornell)](https://github.com/cornell-tech/financial-data-science) — slide decks pairing with AFML chapters

### Standard datasets / benchmarks
- Simulated random-walk strategies (`n_trials=1000` independent zero-mean strategies on synthetic returns) — the standard sanity check that DSR / PBO correctly flag the best as overfit
- The 200+ documented "factor zoo" anomalies (Harvey, Liu, Zhu 2016 supplementary list) — the canonical real-data benchmark for multiple-testing-adjusted significance

### Last cross-checked
2026-05-20 — via WebSearch verification of all SSRN/DOI/JSTOR links + cross-check of `mlfinlab` API surface against current documentation.
