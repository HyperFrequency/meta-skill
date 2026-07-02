# Methodology — CV Schemes, Metrics, PBO

The full four-step evaluation framework. SKILL.md carries the summary; this is the detail.

## Step 1 — Pick the CV scheme that matches the data dependency structure

Three families, in increasing order of statistical rigor:

### Walk-forward analysis
Standard for trading. Train on [t0, t1], test on [t1, t2], step forward, repeat. Two flavors:

- **Anchored:** train window always starts at t0, grows over time. Models see all history.
- **Rolling:** train window has fixed length, slides forward. Models adapt to recent regimes.

Use anchored when you believe the underlying signal is stationary; rolling when you suspect regime change. Or run both and look at the gap — large gap = regime sensitivity.

### Purged + embargoed K-fold
From López de Prado (2018, Ch. 7). Lets you use multiple test windows on the same history (more statistical power than walk-forward) while preventing leakage:

- **Purging:** for each test fold, remove from the training set any samples whose label-end-time falls inside the test fold. This is what makes overlapping triple-barrier labels safe.
- **Embargo:** also remove training samples in a small window *after* the test fold ends. This prevents leakage through serial correlation in features.

The combination is what makes K-fold valid on financial data.

### Combinatorial Purged CV (CPCV)
From López de Prado (2018, Ch. 12). The strongest variant. Instead of N folds with N test sets, partition the data into N groups and form *all combinations* of K test groups (for some K < N). This gives you `C(N, K)` backtest paths through the data, not just N. Far more statistical power, and the resulting distribution of metrics is what feeds into PBO.

Use CPCV when: you have enough data, the label dependence is well-characterized, and you intend to compute PBO. Otherwise use purged K-fold.

## Step 2 — Compute three families of metrics

### Classification metrics (when the model predicts direction or class)
- **Precision / Recall on the positive direction** — more informative than accuracy. Use when class imbalance exists.
- **F1** — harmonic mean of precision and recall.
- **AUC** — ranks predictions; insensitive to threshold. Diagnostic only.
- **Always alongside the unconditional baseline** — what would random guessing at the same class frequency achieve? If the model isn't beating that, it has no edge.

### Regression metrics (when the model predicts return magnitude)
- **MAE** — robust to outliers.
- **RMSE** — penalizes large errors more.
- **MAPE** — scale-free but undefined when actual is zero. Avoid for returns.
- **R² out-of-sample** — for financial returns, expect R² in the 0.005-0.05 range even for good models. A reported R² of 0.5 is almost certainly leakage.

### Trading metrics (the ones that actually matter)
- **Annualized Sharpe ratio** = mean(returns) / std(returns) × √(periods per year). Deflate it (see `ml-hypothesis-design`).
- **Sortino ratio** = mean(returns) / std(negative returns). Doesn't penalize upside volatility.
- **Calmar ratio** = annualized return / max drawdown. The "how much pain for how much gain" ratio.
- **Maximum drawdown** — peak-to-trough loss. The number that gets you fired.
- **Turnover and net-of-cost Sharpe** — always compute Sharpe after realistic transaction costs. A gross Sharpe of 2 with 1000% annual turnover at 5bps round-trip is a net Sharpe of -1.5.
- **Win rate, profit factor** — diagnostic; not standalone evidence.

**Rule of priority:** if classification and trading metrics disagree, trading metrics win. The model exists to make money, not to predict labels.

## Step 3 — Compute the Probability of Backtest Overfitting (PBO)

PBO (Bailey, Borwein, López de Prado, Zhu, 2014/2017) operationalizes the question: "if I picked the in-sample-best strategy, what's the probability it underperforms the median strategy out-of-sample?" The recipe:

1. Run N candidate models. For each, get a time series of returns.
2. Use CPCV (or just bootstrap the time series in non-overlapping blocks) to split into many (in-sample, out-of-sample) pairs.
3. For each pair, rank strategies by IS performance; check the OOS rank of the IS-winner.
4. PBO = fraction of pairs where the IS-winner had a below-median OOS rank.

A PBO ≥ 0.5 means the IS-winner is essentially random in OOS. Any sweep with PBO > 0.5 is overfit by definition. A PBO ≤ 0.05 is the conventional ship threshold.

## Step 4 — Report the full picture

A trading model evaluation report should include:
- The CV scheme used (with embargo window, purge rule)
- All three metric families on out-of-sample data
- Equity curve and drawdown curve
- Deflated Sharpe and PBO
- Performance by regime (vol-up / vol-down, trend / chop) — if it only works in one regime, that's important
- Cost-sensitivity (Sharpe at 0, 1, 5, 10 bps round-trip)

This is what feeds the `tearsheet-generator` skill.

## Common Pitfalls

1. **Reporting a single OOS Sharpe as if it were the strategy's expected Sharpe.** OOS Sharpe is one draw from a distribution. Report the distribution (CPCV or block-bootstrap), not a point.
2. **Using `sklearn.model_selection.KFold` directly.** It shuffles. On time series this is fatal. Use the purged variant or `TimeSeriesSplit` as a bare minimum.
3. **Computing Sharpe on log returns and reporting it as if on simple returns.** Small Sharpe values are close; large ones diverge. Be consistent and document which.
4. **Ignoring costs.** A "great" gross strategy can be a losing net strategy. Report Sharpe at multiple cost levels and choose the realistic one as your headline.
5. **Confusing AUC with profitability.** A model can have AUC = 0.6 and lose money if the marginal-profit trades are systematically wrong-sized or wrong-timed. Validate on PnL, not on rank metrics.
6. **Reporting Calmar without context.** Calmar is dominated by tail events. A strategy with 1 year of clean returns and 1 month of disaster has misleadingly bad Calmar. Pair with rolling Calmar across multiple windows.
7. **Stopping at "passed CV".** Passing purged-CV is necessary but not sufficient. You also need: deflated Sharpe (`ml-hypothesis-design`), regime robustness, cost sensitivity, and a sane equity curve.
8. **Not computing PBO when running a sweep.** If you tried N variants and report the best, you owe PBO. No exceptions.
