# References & Bibliography

Curated, link-verified sources backing the methodology in `SKILL.md`.

## Primary library

This skill is methodology-first; the operational backbone is `mlfinlab` (the
reference implementation of Lopez de Prado's algorithms) plus `scipy.stats` for
power calculations and `statsmodels.stats.multitest` for multiple-testing
corrections.

- [mlfinlab on GitHub](https://github.com/hudson-and-thames/mlfinlab) — Hudson & Thames implementation of Lopez de Prado's AFML algorithms; includes `BacktestStatistics` (deflated Sharpe), PBO, CSCV
- [mlfinlab documentation](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/) — pinned to v1.x
- [scipy.stats](https://docs.scipy.org/doc/scipy/reference/stats.html) — `norm`, `t`, `chi2`, `binom_test` for the underlying power calculations
- [statsmodels.stats.multitest](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) — `multipletests` for Bonferroni / Holm / FDR-BH corrections

## Deep-dive docs (specific pages worth bookmarking)

- [mlfinlab `BacktestStatistics`](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/backtest_statistics/backtest_statistics.html) — operational deflated Sharpe + probabilistic Sharpe; the snippets in this skill mirror this API
- [mlfinlab CSCV / PBO module](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/cross_validation/combinatorial_purged_cv.html) — combinatorial purged CV that feeds PBO
- [statsmodels `power` module](https://www.statsmodels.org/stable/stats.html#power-and-sample-size-calculations) — `tt_solve_power`, `zt_ind_solve_power` for sample-size requirements before the experiment
- [scipy.special.erfinv](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.erfinv.html) — used in the extreme-value approximation for `expected_max_sharpe`
- [statsmodels `multipletests`](https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html) — Bonferroni, Holm, BH-FDR, BY-FDR; pick by your false-discovery budget

## Adjacent / alternative libraries

- [arch.bootstrap.SPA](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html) — Hansen's Superior Predictive Ability test; the statistically formal alternative to "best Sharpe of N"
- [arch.bootstrap.MCS](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html) — Model Confidence Set (Hansen, Lunde, Nason 2011); pick the set of strategies indistinguishable from the best
- [pingouin](https://pingouin-stats.org/) — friendlier wrapper around scipy/statsmodels for power, effect-size, and multiple-comparisons; good for write-ups
- [riskfolio-lib](https://github.com/dcajasn/Riskfolio-Lib) — when the trial-budget question concerns portfolio weights instead of feature/model variants

## Academic papers

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

## Tutorials & write-ups

- [QuantConnect "Probabilistic Sharpe Ratio" research notebook](https://www.quantconnect.com/research/17112/probabilistic-sharpe-ratio/) — interactive walkthrough of PSR / DSR on real strategies
- [Hudson & Thames "Backtest Overfitting" series](https://hudsonthames.org/articles/) — practical PBO + DSR write-ups with code
- [Marcos Lopez de Prado lectures (Cornell)](https://github.com/cornell-tech/financial-data-science) — slide decks pairing with AFML chapters

## Standard datasets / benchmarks

- Simulated random-walk strategies (`n_trials=1000` independent zero-mean strategies on synthetic returns) — the standard sanity check that DSR / PBO correctly flag the best as overfit
- The 200+ documented "factor zoo" anomalies (Harvey, Liu, Zhu 2016 supplementary list) — the canonical real-data benchmark for multiple-testing-adjusted significance

## Last cross-checked

2026-05-20 — via WebSearch verification of all SSRN/DOI/JSTOR links + cross-check of `mlfinlab` API surface against current documentation.
