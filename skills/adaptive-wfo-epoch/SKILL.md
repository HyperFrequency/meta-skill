---
name: adaptive-wfo-epoch
version: 0.1.0
description: >
  Adaptive epoch selection for Walk-Forward Optimization (WFO): picks the per-fold training-epoch count by maximizing Walk-Forward Efficiency (WFE = OOS_Sharpe / IS_Sharpe), builds the WFE-vs-cost efficient frontier, and Bayesian-smooths the choice across folds with look-ahead-safe nested splits. Use when the question is HOW MANY EPOCHS / WHEN TO STOP TRAINING in walk-forward. Trigger even without "epoch" on phrases like "walk-forward efficiency", "WFE", "how many epochs to train", "carry the epoch across folds", "efficient frontier of epochs", "overfitting epochs". Do NOT use for: is-this-Sharpe-real / PBO / purged/combinatorial CV / deflated Sharpe (use "model-evaluation"); comparing a backtest to an Optuna/Ray baseline (use "strategy-verify"); distributed Optuna/Ray HPO fan-out (use "neuro-quant-distributed-optimization"); tearsheets / MAE / leverage (use "tearsheet-generator" / quantstats-rs); porting frameworks (use "strategy-translator"); running the backtest (use "vectorbt" or "nautilus-trader").
allowed-tools: Read, Grep, Glob, Bash
license: HyperFrequency original (citations to external academic + library work)
metadata:
    skill-author: HyperFrequency
    skill-domain: quant-ml-validation
---

# Adaptive Walk-Forward Epoch Selection (AWFES)

Lean router for adaptive epoch selection within Walk-Forward Optimization (WFO).
Optimizes training epochs per-fold via Walk-Forward Efficiency
(**WFE = OOS_Sharpe / IS_Sharpe**), picks from a WFE-vs-cost efficient frontier,
and Bayesian-smooths the choice across folds with look-ahead-safe nested splits.
Each section states the idea and points to the `references/` deep-dive with the
runnable implementation.

## When to Use

- Selecting optimal training epochs for ML models in WFO.
- Avoiding overfitting via Walk-Forward Efficiency metrics.
- Per-fold adaptive epoch selection; efficient frontiers for epoch/cost trade-offs.
- Carrying epoch priors across WFO folds.

See the frontmatter `description` for the WHEN-NOT boundaries (model-evaluation,
strategy-verify, distributed-optimization, tearsheet-generator, etc.).

## Required Tooling

Self-contained — ships formulas and Python snippets, calls **no MCP servers**.
Uses only `Read`/`Grep`/`Glob` to load `references/` deep-dives and `Bash` to run
the epoch-sweep / WFE snippets against your own training loop. Sharpe / PSR / DSR
inputs come from your existing backtest metrics (see sibling cross-links below).

## Quick Start

```python
from adaptive_wfo_epoch import AWFESConfig, compute_efficient_frontier

# Log-spaced epoch candidates from search bounds → [100, 211, 447, 945, 2000]
config = AWFESConfig.from_search_space(min_epoch=100, max_epoch=2000, granularity=5)

for fold in wfo_folds:
    epoch_metrics = []
    for epoch in config.epoch_configs:
        is_sharpe, oos_sharpe = train_and_evaluate(fold, epochs=epoch)
        wfe = config.compute_wfe(is_sharpe, oos_sharpe, n_samples=len(fold.train))
        epoch_metrics.append({"epoch": epoch, "wfe": wfe, "is_sharpe": is_sharpe})
    selected_epoch = compute_efficient_frontier(epoch_metrics)
    prior_epoch = selected_epoch  # carry forward to next fold
```

Full `AWFESConfig`, `compute_is_sharpe_threshold`, and `compute_efficient_frontier`
implementations live in
[references/configuration-guardrails.md](./references/configuration-guardrails.md).

## Methodology Overview

**What this is:** per-fold adaptive epoch selection — (1) train across an epoch
range, (2) compute WFE per epoch, (3) find the efficient frontier (WFE vs cost),
(4) select the optimal epoch for OOS, (5) carry it forward as a Bayesian prior.

**What this is NOT:**

- **NOT early stopping** — that monitors validation loss continuously; this
  evaluates discrete epoch candidates post-hoc.
- **NOT Bayesian optimization** — no surrogate model; direct evaluation of all candidates.
- **NOT nested cross-validation** — uses temporal WFO, not shuffled splits.

## Core Formula & Configuration

`WFE = OOS_Sharpe / IS_Sharpe`. Guidelines (not hard thresholds): ≥0.70 excellent,
0.50–0.70 good, 0.30–0.50 investigate, <0.30 severe overfit. WFE is returned as
`None` when `|IS_Sharpe|` is below the data-driven noise floor
`compute_is_sharpe_threshold(n) = 2/√n`.

All parameters are derived from the search space or data — no magic numbers.
`AWFESConfig` log-spaces epoch candidates and derives the Bayesian prior /
observation variances (95% prior coverage → `σ = range/3.92`; obs var = prior/4).

→ [references/configuration-guardrails.md](./references/configuration-guardrails.md)
for `AWFESConfig`, the IS_Sharpe threshold, annualization factors, the efficient
frontier, and the carry-forward state machine.

## Guardrails

| # | Guardrail | Principle |
| - | --------- | --------- |
| G1 | WFE thresholds (0.30 reject / 0.50 warn / 0.70 target) | Practitioner consensus, adjust to domain |
| G2 | IS_Sharpe minimum is data-driven (`2/√n`), not fixed | Below noise floor → WFE invalid |
| G3 | Adaptive stability penalty on epoch changes | Require improvement > 1σ of WFE history (5–20%) |
| G4 | DSR deflation for epoch-search multiplicity | Corrects expected-max-Sharpe under null (Gumbel) |

→ Full code (`classify_wfe`, `AdaptiveStabilityPenalty`,
`adjusted_dsr_for_epoch_search`) in
[references/configuration-guardrails.md](./references/configuration-guardrails.md).

## WFE Aggregation

**Under the null (no skill), WFE follows a Cauchy distribution** — no defined
mean or variance, heavy tails. Arithmetic mean is unreliable; a single extreme
fold dominates. **Prefer median or pooled** aggregation.

Pick by scenario: variable fold sizes → **pooled WFE** (weights by precision);
suspected outliers → **median WFE** (robust); homogeneous folds → **inverse-var
mean** (optimal); reporting → all three (cross-check).

→ Implementations + the proof `WFE | H0 ~ Cauchy(0, √(T_IS/T_OOS))` in
[references/mathematical-formulation.md](./references/mathematical-formulation.md).

## Anti-Patterns

- **CRITICAL — expanding window (range bars):** never use it for range-bar ML
  training; it causes fold non-equivalence, regime dilution, and biased risk
  metrics. Use a fixed sliding window.
- **HIGH:** peak picking (best epoch at sweep boundary → expand range), too few
  folds (effective_n < 30), ignoring temporal autocorrelation (purge/gap folds),
  overfitting to IS (IS ≫ OOS → fewer epochs + regularization), meta-overfitting
  (limit to 3–4 epoch candidates).
- **MEDIUM:** `sqrt(252)` for crypto (use `sqrt(365)` / `sqrt(7)` weekly), single
  epoch selection with no uncertainty (report a CI).

→ Symptoms, detection code, and fixes (incl. Section 7) in
[references/anti-patterns.md](./references/anti-patterns.md).

## Decision Tree

```
IS_Sharpe > compute_is_sharpe_threshold(n)?  ──NO──> WFE invalid, use fallback
  │ YES                                               (threshold = 2/√n)
Compute WFE per epoch  ──any WFE > 0.30?  ──NO──> REJECT all (severe overfit)
  │ YES
Compute efficient frontier
  │
Apply AdaptiveStabilityPenalty (threshold from WFE variance)
  └─> Return selected epoch
```

→ Full practitioner tree in
[references/epoch-selection-decision-tree.md](./references/epoch-selection-decision-tree.md).

## OOS Application (Nested WFO + Bayesian Lag)

AWFES uses **Nested WFO** with three temporally-ordered splits per fold and 6%
embargo gaps at each boundary:

```
[ Train 60% ] -gap- [ Val 20% ] -gap- [ Test 20% ]
```

Per fold: sweep epochs on Train → compute WFE on Val → Bayesian-update the
posterior → train the final model at the smoothed epoch → evaluate once on Test.
Epoch selection never touches Test data.

→ Full `AWFESOOSApplication` class and per-fold workflow in
[references/oos-application.md](./references/oos-application.md).

## Epoch Smoothing

Raw per-fold optima are noisy (limited val data, regime shifts, stochastic
training). Smooth to reduce variance while preserving signal.

Methods: **Bayesian (recommended)** — principled, handles uncertainty; **EMA** —
simple/responsive; **SMA** — most stable; **Median** — robust to outliers. The
Bayesian smoother weights each observation by WFE (clamped to [0.1, 2.0]) and uses
a precision-weighted Normal-Normal update with variances derived from the search
space.

→ `BayesianEpochSmoother`, EMA/SMA/Median smoothers, and initialization
strategies in [references/epoch-smoothing.md](./references/epoch-smoothing.md).

## OOS Metrics (Test Evaluation)

Compute on **Test** data only. For range bars use time-weighted Sharpe
(`sharpe_tw`), not simple bar Sharpe — see
[references/range-bar-metrics.md](./references/range-bar-metrics.md). Three tiers:
**(1) Primary** (`sharpe_tw`, `hit_rate`, `wfe_test`), **(2) Risk**
(`max_drawdown`, `calmar_ratio`, `profit_factor`, `cvar_10pct`), **(3) Statistical**
(`psr`, `dsr`, `binomial_pvalue`, `hac_ttest_pvalue`).

→ Full metric list, acceptance gates, formulas, code, and threshold
justifications in [references/oos-metrics.md](./references/oos-metrics.md).

## Look-Ahead Bias Prevention

Using a fold's own optimal epoch on that fold's test set leaks information.
**The v3 rule: Test must use `prior_bayesian_epoch` (from PRIOR folds only), NOT
`val_optimal_epoch`.** Obtain the prior epoch *before* any work on the current
fold; update the Bayesian posterior *after* test evaluation (for future folds).

Embargoes: 6% of fold at Train→Val and Val→Test; ≥1 calendar hour Fold→Fold.
**Pre-run checklist:** three-way split separated · 6% embargoes · Bayesian lag ·
Test untouched until final eval · strict temporal order · per-split feature scaling.

→ v2-bug-vs-v3-fix walkthrough, embargo indices, and the four bias anti-patterns
in [references/look-ahead-bias.md](./references/look-ahead-bias.md).

## Cross-Links to Sibling Skills

This skill owns **WFO epoch selection / overfitting-epoch control** only. Hand off:

| If you need...                                                                  | Use sibling                            |
| ------------------------------------------------------------------------------- | -------------------------------------- |
| Is this Sharpe real? PBO / purged + embargoed / combinatorial CV / deflated Sharpe | `model-evaluation`                  |
| Compare a backtest to an Optuna/Ray baseline; root-cause logic discrepancies    | `strategy-verify`                      |
| Distributed Optuna / Ray / Dask HPO fan-out + MLflow / Postgres storage         | `neuro-quant-distributed-optimization` |
| Performance tearsheet / MAE analysis / optimal-leverage                         | `tearsheet-generator` (quantstats-rs)  |
| Port the strategy to vectorbt / Nautilus / Pine v6 / Rust / C++ / from a paper  | `strategy-translator`                  |
| Author or run the backtest itself (vectorized vs event-driven)                  | `vectorbt` / `nautilus-trader`         |
| Feature pipeline construction                                                   | `feature-engineering`                  |

## References (deep-dives under `references/`)

Most are linked inline above. Full index under `./references/`:
`configuration-guardrails.md` · `mathematical-formulation.md` ·
`epoch-selection-decision-tree.md` · `anti-patterns.md` · `oos-application.md` ·
`epoch-smoothing.md` · `oos-metrics.md` · `look-ahead-bias.md` ·
`range-bar-metrics.md` · `feature-sets.md` (feature definitions) ·
`xlstm-implementation.md` (xLSTM training loop) · `academic-foundations.md`.

Key citations (Pardo 2008; Bailey & López de Prado 2014; López de Prado 2018 Ch. 7;
Bischl et al. 2023; Nomura & Ono 2021) in
[academic-foundations.md](./references/academic-foundations.md).

## Troubleshooting

Common failure → fix table (WFE is None, all epochs rejected, unstable posterior,
boundary epochs, detected look-ahead bias, over-aggressive DSR, Cauchy mean
issues, inconsistent fold metrics) lives in
[references/configuration-guardrails.md](./references/configuration-guardrails.md#troubleshooting).
