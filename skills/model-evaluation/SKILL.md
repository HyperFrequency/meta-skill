---
name: model-evaluation
description: "Evaluate ML trading models with techniques specific to financial time series, not generic ML. Use when validating a model whose outputs will be traded — for cross-validation under temporal dependence (walk-forward, purged + embargoed K-fold, Combinatorial Purged CV), for computing trading metrics (Sharpe, Calmar, Sortino, max drawdown) alongside ML metrics, and for the deflated/PBO discipline that separates real edges from data-mining artifacts. Triggers on phrases like \"evaluate this model\", \"validate this strategy\", \"walk-forward analysis\", \"purged CV\", \"combinatorial CV\", \"PBO\", \"probability of backtest overfitting\", \"calmar ratio\", \"is this Sharpe real\", \"what metrics should I report\". Strong opinion: do NOT use raw k-fold or accuracy-without-baseline. For pre-experiment power calc use ml-hypothesis-design; for feature pipeline issues use feature-engineering."
allowed-tools: Read Write Edit Bash
---

# Model Evaluation for Trading Models

## Overview

Generic ML evaluation — `train_test_split`, K-fold CV, accuracy — does not work for trading models. Returns are autocorrelated, labels leak forward in time, and the same dataset has been mined by every quant since 2010. A model that scores 60% accuracy on the test fold can lose money in production because the 60% was on the wrong question.

This skill is the evaluation discipline that catches those failures. It enforces the temporal structure of financial data (no random splits, no shuffling), the right metrics (trading metrics dominate; ML metrics are diagnostic), and the multiple-testing posture (PBO, deflated Sharpe). It has strong opinions about what NOT to use.

## When to Use This Skill

Use this skill when:

- A model is fit and you need to validate it before trading
- Choosing a CV scheme for a financial time-series problem
- Reporting performance to a stakeholder and need to pick the right metrics
- A model passed K-fold beautifully but is failing live and you need to diagnose why
- Designing a walk-forward backtest and need to set the train/test/embargo windows
- Computing PBO or deflated Sharpe over a parameter sweep

Do **not** use this for: the experiment design stage before fitting (use `ml-hypothesis-design`); or feature pipeline construction (use `feature-engineering`).

## Strong Opinions: What NOT to Use

These are non-negotiable in this skill:

1. **Do not use random K-fold CV on time series.** The folds will contain future data leaking into past training. The metric will be optimistic by 1.5-3× in practice.
2. **Do not use shuffled `train_test_split`.** Same problem.
3. **Do not report directional accuracy without a baseline.** A 52% directional model on a market that is up 53% of days has zero edge. Always compare to the unconditional class frequency.
4. **Do not optimize for raw Sharpe without deflating it.** A Sharpe of 1.5 from a 100-trial sweep is approximately a Sharpe of 0.5 in expectation. See `ml-hypothesis-design`.
5. **Do not report ML metrics (AUC, F1) as if they were trading metrics.** A model can have high AUC and lose money — particularly when costs eat the marginal-profit trades that drive the ROC curve.
6. **Do not evaluate on a single fold or single OOS period.** One sample is one outcome from a distribution; you don't know the variance.

## Core Framework

### Step 1 — Pick the CV scheme that matches the data dependency structure

Three families, in increasing order of statistical rigor:

#### Walk-forward analysis
Standard for trading. Train on [t0, t1], test on [t1, t2], step forward, repeat. Two flavors:

- **Anchored:** train window always starts at t0, grows over time. Models see all history.
- **Rolling:** train window has fixed length, slides forward. Models adapt to recent regimes.

Use anchored when you believe the underlying signal is stationary; rolling when you suspect regime change. Or run both and look at the gap — large gap = regime sensitivity.

#### Purged + embargoed K-fold
From López de Prado (2018, Ch. 7). Lets you use multiple test windows on the same history (more statistical power than walk-forward) while preventing leakage:

- **Purging:** for each test fold, remove from the training set any samples whose label-end-time falls inside the test fold. This is what makes overlapping triple-barrier labels safe.
- **Embargo:** also remove training samples in a small window *after* the test fold ends. This prevents leakage through serial correlation in features.

The combination is what makes K-fold valid on financial data.

#### Combinatorial Purged CV (CPCV)
From López de Prado (2018, Ch. 12). The strongest variant. Instead of N folds with N test sets, partition the data into N groups and form *all combinations* of K test groups (for some K < N). This gives you `C(N, K)` backtest paths through the data, not just N. Far more statistical power, and the resulting distribution of metrics is what feeds into PBO.

Use CPCV when: you have enough data, the label dependence is well-characterized, and you intend to compute PBO. Otherwise use purged K-fold.

### Step 2 — Compute three families of metrics

#### Classification metrics (when the model predicts direction or class)
- **Precision / Recall on the positive direction** — more informative than accuracy. Use when class imbalance exists.
- **F1** — harmonic mean of precision and recall.
- **AUC** — ranks predictions; insensitive to threshold. Diagnostic only.
- **Always alongside the unconditional baseline** — what would random guessing at the same class frequency achieve? If the model isn't beating that, it has no edge.

#### Regression metrics (when the model predicts return magnitude)
- **MAE** — robust to outliers.
- **RMSE** — penalizes large errors more.
- **MAPE** — scale-free but undefined when actual is zero. Avoid for returns.
- **R² out-of-sample** — for financial returns, expect R² in the 0.005-0.05 range even for good models. A reported R² of 0.5 is almost certainly leakage.

#### Trading metrics (the ones that actually matter)
- **Annualized Sharpe ratio** = mean(returns) / std(returns) × √(periods per year). Deflate it (see `ml-hypothesis-design`).
- **Sortino ratio** = mean(returns) / std(negative returns). Doesn't penalize upside volatility.
- **Calmar ratio** = annualized return / max drawdown. The "how much pain for how much gain" ratio.
- **Maximum drawdown** — peak-to-trough loss. The number that gets you fired.
- **Turnover and net-of-cost Sharpe** — always compute Sharpe after realistic transaction costs. A gross Sharpe of 2 with 1000% annual turnover at 5bps round-trip is a net Sharpe of -1.5.
- **Win rate, profit factor** — diagnostic; not standalone evidence.

**Rule of priority:** if classification and trading metrics disagree, trading metrics win. The model exists to make money, not to predict labels.

### Step 3 — Compute the Probability of Backtest Overfitting (PBO)

PBO (Bailey, Borwein, López de Prado, Zhu, 2014/2017) operationalizes the question: "if I picked the in-sample-best strategy, what's the probability it underperforms the median strategy out-of-sample?" The recipe:

1. Run N candidate models. For each, get a time series of returns.
2. Use CPCV (or just bootstrap the time series in non-overlapping blocks) to split into many (in-sample, out-of-sample) pairs.
3. For each pair, rank strategies by IS performance; check the OOS rank of the IS-winner.
4. PBO = fraction of pairs where the IS-winner had a below-median OOS rank.

A PBO ≥ 0.5 means the IS-winner is essentially random in OOS. Any sweep with PBO > 0.5 is overfit by definition. A PBO ≤ 0.05 is the conventional ship threshold.

### Step 4 — Report the full picture

A trading model evaluation report should include:
- The CV scheme used (with embargo window, purge rule)
- All three metric families on out-of-sample data
- Equity curve and drawdown curve
- Deflated Sharpe and PBO
- Performance by regime (vol-up / vol-down, trend / chop) — if it only works in one regime, that's important
- Cost-sensitivity (Sharpe at 0, 1, 5, 10 bps round-trip)

This is what feeds the `tearsheet-generator` skill.

## Code Snippets

### Purged K-fold CV (López de Prado)

```python
import numpy as np
import pandas as pd
from sklearn.model_selection._split import _BaseKFold


class PurgedKFold(_BaseKFold):
    """K-fold CV that purges training samples whose label end-time falls inside the test fold,
    and optionally embargoes a window after each test fold.

    Reference: López de Prado (2018), Advances in Financial Machine Learning, Ch. 7.
    """

    def __init__(self, n_splits: int, t1: pd.Series, embargo_pct: float = 0.01):
        super().__init__(n_splits=n_splits, shuffle=False, random_state=None)
        if not isinstance(t1, pd.Series):
            raise TypeError("t1 must be a pd.Series indexed by event start time")
        self.t1 = t1
        self.embargo_pct = embargo_pct

    def split(self, X: pd.DataFrame, y=None, groups=None):
        if (X.index != self.t1.index).any():
            raise ValueError("X.index and t1.index must match")

        indices = np.arange(X.shape[0])
        embargo = int(X.shape[0] * self.embargo_pct)

        # Test folds are contiguous blocks of indices
        test_starts = [(i[0], i[-1] + 1) for i in
                       np.array_split(indices, self.n_splits)]

        for start, end in test_starts:
            test_idx = indices[start:end]
            t0 = self.t1.index[start]
            t1_test = self.t1.iloc[end - 1]

            # PURGE: drop training samples whose label end time is inside the test window
            train_idx = self.t1.index[(self.t1 < t0) | (self.t1.index > t1_test)]
            train_pos = X.index.get_indexer(train_idx)
            train_pos = train_pos[train_pos >= 0]

            # EMBARGO: drop the `embargo` indices immediately following the test fold
            if embargo > 0:
                embargo_end = min(end + embargo, len(indices))
                embargo_idx = indices[end:embargo_end]
                train_pos = np.setdiff1d(train_pos, embargo_idx)

            yield train_pos, test_idx
```

### Walk-forward backtest loop

```python
def walk_forward(
    X: pd.DataFrame,
    y: pd.Series,
    model_factory,
    train_size: int,
    test_size: int,
    step: int = None,
    anchored: bool = False,
) -> pd.DataFrame:
    """Walk-forward predictions for a time-ordered dataset.

    Args:
        X, y: feature matrix and target, sorted by time.
        model_factory: callable returning a fresh sklearn-like model each window.
        train_size: number of samples in each training window.
        test_size: number of samples to predict in each step.
        step: stride between windows; defaults to test_size (non-overlapping).
        anchored: if True, training window grows from index 0; else it slides.

    Returns:
        DataFrame with columns ['y_true', 'y_pred', 'fold'] indexed by X.index.
    """
    step = step or test_size
    out = []
    fold = 0
    start = train_size
    while start + test_size <= len(X):
        train_lo = 0 if anchored else start - train_size
        Xtr = X.iloc[train_lo:start]
        ytr = y.iloc[train_lo:start]
        Xte = X.iloc[start:start + test_size]
        yte = y.iloc[start:start + test_size]

        model = model_factory()
        model.fit(Xtr, ytr)
        yhat = model.predict(Xte)

        out.append(pd.DataFrame({
            "y_true": yte.values,
            "y_pred": yhat,
            "fold": fold,
        }, index=Xte.index))
        fold += 1
        start += step

    return pd.concat(out)
```

### Trading metrics from a returns series

```python
def trading_metrics(returns: pd.Series, periods_per_year: int = 252) -> dict:
    """Compute a standard tearsheet bundle from a per-period returns series."""
    r = returns.dropna()
    if len(r) < 2:
        return {}

    ann_factor = np.sqrt(periods_per_year)
    mean_r = r.mean()
    std_r = r.std()
    downside_std = r[r < 0].std()

    sharpe = (mean_r / std_r) * ann_factor if std_r > 0 else np.nan
    sortino = (mean_r / downside_std) * ann_factor if downside_std > 0 else np.nan

    cum = (1 + r).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    max_dd = drawdown.min()

    ann_return = (1 + mean_r) ** periods_per_year - 1
    calmar = ann_return / abs(max_dd) if max_dd != 0 else np.nan

    return {
        "annualized_return": ann_return,
        "annualized_vol": std_r * ann_factor,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_dd,
        "win_rate": (r > 0).mean(),
        "profit_factor": r[r > 0].sum() / -r[r < 0].sum() if (r < 0).any() else np.nan,
    }
```

### Probability of Backtest Overfitting (PBO)

```python
from itertools import combinations


def probability_of_backtest_overfitting(
    returns_matrix: pd.DataFrame,
    n_partitions: int = 16,
) -> float:
    """PBO over a matrix of strategy returns.

    Args:
        returns_matrix: T x N DataFrame, T time periods, N strategies, per-period returns.
        n_partitions: number of equal-length non-overlapping submatrices to split T into.
                      Must be even; combinations of n_partitions/2 form the IS sets.

    Returns:
        PBO ∈ [0, 1]: fraction of CPCV splits where the IS-winner ranks below OOS-median.

    Reference: Bailey, Borwein, López de Prado, Zhu (2014/2017),
    "The Probability of Backtest Overfitting", Journal of Computational Finance.
    """
    assert n_partitions % 2 == 0, "n_partitions must be even"

    # Split rows into n_partitions equal blocks
    blocks = np.array_split(returns_matrix.index, n_partitions)
    block_returns = [returns_matrix.loc[b] for b in blocks]

    # Each split: choose n/2 blocks as IS, rest as OOS
    is_block_idx_combos = list(combinations(range(n_partitions), n_partitions // 2))

    fail_count = 0
    for is_idx in is_block_idx_combos:
        oos_idx = [i for i in range(n_partitions) if i not in is_idx]
        is_returns = pd.concat([block_returns[i] for i in is_idx])
        oos_returns = pd.concat([block_returns[i] for i in oos_idx])

        # Use Sharpe as the ranking metric
        is_sharpe  = is_returns.mean() / is_returns.std()
        oos_sharpe = oos_returns.mean() / oos_returns.std()

        is_winner = is_sharpe.idxmax()
        oos_rank_of_winner = oos_sharpe.rank().loc[is_winner]
        oos_median_rank = (len(oos_sharpe) + 1) / 2

        if oos_rank_of_winner < oos_median_rank:
            fail_count += 1

    return fail_count / len(is_block_idx_combos)
```

## Common Pitfalls

1. **Reporting a single OOS Sharpe as if it were the strategy's expected Sharpe.** OOS Sharpe is one draw from a distribution. Report the distribution (CPCV or block-bootstrap), not a point.
2. **Using `sklearn.model_selection.KFold` directly.** It shuffles. On time series this is fatal. Use the purged variant or `TimeSeriesSplit` as a bare minimum.
3. **Computing Sharpe on log returns and reporting it as if on simple returns.** Small Sharpe values are close; large ones diverge. Be consistent and document which.
4. **Ignoring costs.** A "great" gross strategy can be a losing net strategy. Report Sharpe at multiple cost levels and choose the realistic one as your headline.
5. **Confusing AUC with profitability.** A model can have AUC = 0.6 and lose money if the marginal-profit trades are systematically wrong-sized or wrong-timed. Validate on PnL, not on rank metrics.
6. **Reporting Calmar without context.** Calmar is dominated by tail events. A strategy with 1 year of clean returns and 1 month of disaster has misleadingly bad Calmar. Pair with rolling Calmar across multiple windows.
7. **Stopping at "passed CV".** Passing purged-CV is necessary but not sufficient. You also need: deflated Sharpe (`ml-hypothesis-design`), regime robustness, cost sensitivity, and a sane equity curve.
8. **Not computing PBO when running a sweep.** If you tried N variants and report the best, you owe PBO. No exceptions.

## Tooling References

This skill defines methodology. Operationalize it with:

- **`ml-hypothesis-design`** skill (sister skill) — for the Deflated Sharpe and trial-count discipline that pairs with PBO here.
- **`feature-engineering`** skill (sister skill) — provides the `t1` series (label end-times) that PurgedKFold requires.
- **`scikit-learn`** skill — implements `TimeSeriesSplit`, `cross_val_score`, the `_BaseKFold` interface used above.
- **`vectorbt`** skill — for fast vectorized backtests across CV splits and parameter sweeps.
- **`nautilus-trader`** skill — for realistic execution-modeled backtests when the strategy's intraday dynamics matter to the OOS metrics.
- **`tearsheet-generator`** skill — for assembling the metric outputs and equity curves from this skill into a publication-grade tearsheet.
- **`mlfinlab`** (library, not yet a skill) — implements `PurgedKFold`, `CombPurgedKFoldCV`, and PBO canonically; the snippets above are minimal reference implementations.

## References

### Primary library
This skill is methodology-first; the operational backbone is `mlfinlab` (Lopez de Prado's CV + PBO + DSR implementations) and `scikit-learn` for the underlying `_BaseKFold` interface.

- [mlfinlab on GitHub](https://github.com/hudson-and-thames/mlfinlab) — Hudson & Thames; the reference implementation of AFML Ch. 7 / 11 / 12
- [mlfinlab documentation](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/) — pinned to v1.x
- [scikit-learn on GitHub](https://github.com/scikit-learn/scikit-learn) — provides `_BaseKFold`, `TimeSeriesSplit`, the scaffolding the snippets extend
- [arch on GitHub](https://github.com/bashtage/arch) — `MCS`, `SPA`, `StepM` for multiple-comparison-corrected model selection
- [quantstats on GitHub](https://github.com/ranaroussi/quantstats) — Sharpe, Sortino, Calmar, MDD; the trading-metrics module of choice
- [empyrical-reloaded](https://github.com/stefan-jansen/empyrical-reloaded) — the foundation for both quantstats and pyfolio metrics

### Deep-dive docs (specific pages worth bookmarking)
- [mlfinlab PurgedKFold + CombPurgedKFoldCV](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/cross_validation/purged_cross_validation.html) — canonical Ch. 7 implementation; verify your version's API
- [mlfinlab Backtest Statistics](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/backtest_statistics/backtest_statistics.html) — Deflated Sharpe Ratio (DSR), Probabilistic Sharpe Ratio (PSR)
- [mlfinlab Combinatorial CV → PBO](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/cross_validation/combinatorial_purged_cv.html) — CPCV path generation that feeds PBO computation
- [sklearn `TimeSeriesSplit`](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html) — the minimum-viable time-respecting CV; the bare-minimum non-shuffled alternative
- [sklearn `_BaseKFold` source](https://github.com/scikit-learn/scikit-learn/blob/main/sklearn/model_selection/_split.py) — the abstract base the PurgedKFold snippet extends
- [arch `MCS` + `SPA`](https://arch.readthedocs.io/en/latest/multiple-comparison/multiple-comparison-reference.html) — Hansen Model Confidence Set + Superior Predictive Ability tests
- [quantstats stats module source](https://github.com/ranaroussi/quantstats/blob/main/quantstats/stats.py) — Sharpe, Sortino, Calmar, max_drawdown, profit_factor implementations

### Adjacent / alternative libraries
- [pyfolio-reloaded](https://github.com/stefan-jansen/pyfolio-reloaded) — broader risk tearsheet; pairs with the metrics from this skill
- [bt (backtesting)](https://github.com/pmorissette/bt) — strategy-tree evaluation; nice for combining strategies and comparing
- [vectorbt](https://github.com/polakowo/vectorbt) — vectorized backtest; the parameter-sweep engine that produces the input matrix for PBO
- [skfolio](https://github.com/skfolio/skfolio) — newer scikit-learn-style portfolio optimization with built-in walk-forward / cross-validation utilities
- [pingouin](https://pingouin-stats.org/) — for the statistical-significance post-hoc tests on metric distributions

### Academic papers
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

### Tutorials & write-ups
- [Hudson & Thames "Backtest Overfitting" series](https://hudsonthames.org/articles/) — practical PBO + DSR write-ups with mlfinlab code
- [QuantConnect Sharpe ratio research](https://www.quantconnect.com/research/17112/probabilistic-sharpe-ratio/) — interactive PSR / DSR walkthrough on live strategies
- [Marcos Lopez de Prado Cornell lectures](https://github.com/cornell-tech/financial-data-science) — slide decks + code for AFML Ch. 7 / 11 / 12 / 13 / 14
- [Stefan Jansen "Machine Learning for Trading" Ch. 5-7](https://github.com/stefan-jansen/machine-learning-for-trading) — practical walk-forward and CV pipelines

### Standard datasets / benchmarks
- 100 random-walk strategies → CPCV → PBO ≈ 0.5 — the standard sanity check that the PBO procedure correctly flags null results
- A single mean-reverting strategy with known SR=0.5, simulated over 10 years and 100 hyperparameter variants → DSR < 0.95 — the standard "you cherry-picked from too many trials" demonstration
- AFML Ch. 12 worked example (S&P 500 mean-reversion strategy with hyperparameter grid) — the canonical reproduction for CPCV+PBO

### Last cross-checked
2026-05-20 — via WebSearch verification of all paper DOIs/SSRN links + cross-check of mlfinlab / sklearn / arch API surfaces.
