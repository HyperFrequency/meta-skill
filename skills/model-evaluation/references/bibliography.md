# References & Bibliography

Libraries, papers, tutorials, and benchmark datasets backing this skill.

## Primary library
This skill is methodology-first; the operational backbone is `mlfinlab` (Lopez de Prado's CV + PBO + DSR implementations) and `scikit-learn` for the underlying `_BaseKFold` interface.

- [mlfinlab on GitHub](https://github.com/hudson-and-thames/mlfinlab) — Hudson & Thames; the reference implementation of AFML Ch. 7 / 11 / 12
- [mlfinlab documentation](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/) — pinned to v1.x
- [scikit-learn on GitHub](https://github.com/scikit-learn/scikit-learn) — provides `_BaseKFold`, `TimeSeriesSplit`, the scaffolding the snippets extend
- [arch on GitHub](https://github.com/bashtage/arch) — `MCS`, `SPA`, `StepM` for multiple-comparison-corrected model selection
- [quantstats on GitHub](https://github.com/ranaroussi/quantstats) — Sharpe, Sortino, Calmar, MDD; the trading-metrics module of choice
- [empyrical-reloaded](https://github.com/stefan-jansen/empyrical-reloaded) — the foundation for both quantstats and pyfolio metrics

## Deep-dive docs (specific pages worth bookmarking)
- [mlfinlab PurgedKFold + CombPurgedKFoldCV](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/cross_validation/purged_cross_validation.html) — canonical Ch. 7 implementation; verify your version's API
- [mlfinlab Backtest Statistics](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/backtest_statistics/backtest_statistics.html) — Deflated Sharpe Ratio (DSR), Probabilistic Sharpe Ratio (PSR)
- [mlfinlab Combinatorial CV → PBO](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/cross_validation/combinatorial_purged_cv.html) — CPCV path generation that feeds PBO computation
- [sklearn `TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) — the minimum-viable time-respecting CV; the bare-minimum non-shuffled alternative
- [sklearn `_BaseKFold` source](https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/model_selection/_split.py) — the abstract base the PurgedKFold snippet extends
- [arch `MCS` + `SPA`](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html) — Hansen Model Confidence Set + Superior Predictive Ability tests
- [quantstats stats module source](https://github.com/ranaroussi/quantstats/blob/main/quantstats/stats.py) — Sharpe, Sortino, Calmar, max_drawdown, profit_factor implementations

## Adjacent / alternative libraries
- [pyfolio-reloaded](https://github.com/stefan-jansen/pyfolio-reloaded) — broader risk tearsheet; pairs with the metrics from this skill
- [bt (backtesting)](https://github.com/pmorissette/bt) — strategy-tree evaluation; nice for combining strategies and comparing
- [vectorbt](https://github.com/polakowo/vectorbt) — vectorized backtest; the parameter-sweep engine that produces the input matrix for PBO
- [skfolio](https://github.com/skfolio/skfolio) — newer scikit-learn-style portfolio optimization with built-in walk-forward / cross-validation utilities
- [pingouin](https://pingouin-stats.org/) — for the statistical-significance post-hoc tests on metric distributions

## Academic papers
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. ISBN 9781119482086 — the bible.
  - Ch. 7 — Cross-validation in finance (purged + embargoed K-fold)
  - Ch. 11 — Backtest statistics (Sharpe, deflated Sharpe in operational form)
  - Ch. 12 — Backtesting through cross-validation (CPCV)
  - Ch. 13-14 — Backtest overfitting tests (PBO)
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). "The Probability of Backtest Overfitting." *Journal of Computational Finance* 20(4), 39-69. [escholarship.org/uc/item/4w1110bb](https://escholarship.org/uc/item/4w1110bb) — formal PBO paper.
- Bailey, D. H., & López de Prado, M. (2014). "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality." *Journal of Portfolio Management* 40(5), 94-107. [SSRN 2460551](https://papers.ssrn.com/abstract=2460551) — DSR.
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2014). "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance." *Notices of the AMS* 61(5), 458-471. [SSRN 2326253](https://papers.ssrn.com/abstract=2326253) — the polemic companion.
- Sharpe, W. F. (1994). "The Sharpe Ratio." *Journal of Portfolio Management* 21(1), 49-58. [DOI: 10.3905/jpm.1994.409501](https://doi.org/10.3905/jpm.1994.409501) — the canonical Sharpe-ratio reference.
- Bailey, D. H., & López de Prado, M. (2014). "The Sharpe Ratio Efficient Frontier." *Journal of Risk* 15(2), 3-44. [SSRN 1821643](https://papers.ssrn.com/abstract=1821643) — Sharpe under non-normal returns / PSR.
- Hansen, P. R., Lunde, A., & Nason, J. M. (2011). "The Model Confidence Set." *Econometrica* 79(2), 453-497. [DOI: 10.3982/ECTA5771](https://doi.org/10.3982/ECTA5771) — the set-of-best-models alternative to ranking.
- Hansen, P. R. (2005). "A Test for Superior Predictive Ability." *Journal of Business & Economic Statistics* 23(4), 365-380. [DOI: 10.1198/073500105000000063](https://doi.org/10.1198/073500105000000063) — SPA test; the formal answer to "is my best strategy better than the benchmark after considering all the alternatives I tried?"
- Romano, J. P., & Wolf, M. (2005). "Stepwise Multiple Testing as Formalized Data Snooping." *Econometrica* 73(4), 1237-1282. [DOI: 10.1111/j.1468-0262.2005.00615.x](https://doi.org/10.1111/j.1468-0262.2005.00615.x) — stepM; bootstrap-based correlated-test correction.
- Lo, A. W. (2002). "The Statistics of Sharpe Ratios." *Financial Analysts Journal* 58(4), 36-52. [DOI: 10.2469/faj.v58.n4.2453](https://doi.org/10.2469/faj.v58.n4.2453) — the IID Sharpe-ratio sampling distribution.
- Mertens, E. (2002). "Comments on Variance of the IID estimator in Lo (2002)." Working paper — skew/kurt correction for the Sharpe variance.
- Magdon-Ismail, M., & Atiya, A. F. (2004). "Maximum Drawdown." *Risk Magazine* 17(10), 99-102. [PDF (MIT)](http://web.mit.edu/19.0/yarn/papers/MaxDD.pdf) — theoretical distribution of MDD; tells you when an observed drawdown is "unusual."
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). "...and the Cross-Section of Expected Returns." *Review of Financial Studies* 29(1), 5-68. [DOI: 10.1093/rfs/hhv059](https://doi.org/10.1093/rfs/hhv059) — multiple-testing applied to factors; the t > 3 result.

## Tutorials & write-ups
- [Hudson & Thames "Backtest Overfitting" series](https://hudsonthames.org/articles/) — practical PBO + DSR write-ups with mlfinlab code
- [QuantConnect Sharpe ratio research](https://www.quantconnect.com/research/17112/probabilistic-sharpe-ratio/) — interactive PSR / DSR walkthrough on live strategies
- [Marcos Lopez de Prado Cornell lectures](https://github.com/cornell-tech/financial-data-science) — slide decks + code for AFML Ch. 7 / 11 / 12 / 13 / 14
- [Stefan Jansen "Machine Learning for Trading" Ch. 5-7](https://github.com/stefan-jansen/machine-learning-for-trading) — practical walk-forward and CV pipelines

## Standard datasets / benchmarks
- 100 random-walk strategies → CPCV → PBO ≈ 0.5 — the standard sanity check that the PBO procedure correctly flags null results
- A single mean-reverting strategy with known SR=0.5, simulated over 10 years and 100 hyperparameter variants → DSR < 0.95 — the standard "you cherry-picked from too many trials" demonstration
- AFML Ch. 12 worked example (S&P 500 mean-reversion strategy with hyperparameter grid) — the canonical reproduction for CPCV+PBO

## Last cross-checked
2026-05-20 — via WebSearch verification of all paper DOIs/SSRN links + cross-check of mlfinlab / sklearn / arch API surfaces.
