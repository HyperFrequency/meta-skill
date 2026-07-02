---
name: model-evaluation
description: >
  Financial-ML model VALIDATION discipline — separates a real edge from a data-mining artifact. Covers
  CV under temporal dependence (walk-forward, purged/embargoed K-fold, Combinatorial Purged CV / CPCV),
  trading-vs-ML metrics (Sharpe/Sortino/Calmar/MDD, net-of-cost), and the overfitting posture:
  Probability of Backtest Overfitting (PBO) and deflated Sharpe. Triggers on "evaluate this model",
  "validate this strategy", "purged CV", "combinatorial CV", "PBO", "deflated Sharpe", "is this Sharpe
  real", "did I overfit this sweep"; trigger even without "evaluate" on "my k-fold looked great but it's
  losing live". Do NOT use for pre-experiment power/design (use ml-hypothesis-design), feature-pipeline
  construction (feature-engineering), walk-forward EPOCH selection (adaptive-wfo-epoch), or actually
  running the backtest (vectorbt / nautilus-trader). For the tearsheet / MAE / leverage report use
  tearsheet-generator; for comparing to an Optuna/Ray baseline use strategy-verify.
version: "1.0.0"
allowed-tools: Read, Write, Edit, Bash
license: HyperFrequency original (citations to external academic + library work)
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

## Required Tooling

Methodology-first; runs as **pure Python — no MCP servers required**. The reference implementations depend only on `numpy`, `pandas`, and `scikit-learn`; `mlfinlab` is the optional canonical backbone for purged/combinatorial CV, PBO, and the Deflated Sharpe Ratio.

| Dependency | Type | Purpose |
| --- | --- | --- |
| numpy, pandas | Python lib | returns series, block splits, metric math |
| scikit-learn | Python lib | `_BaseKFold`, `TimeSeriesSplit` scaffolding |
| mlfinlab | Python lib (optional) | canonical `PurgedKFold` / `CombPurgedKFoldCV` / PBO / DSR |

No federated MCP tool is invoked here. If you later put a metrics engine behind an MCP server, route it through `/forge` or `mcp2cli` rather than a direct SSE connection.

## Strong Opinions: What NOT to Use

Non-negotiable in this skill:

1. **No random K-fold CV on time series.** Folds leak future data into past training; the metric is optimistic by 1.5-3× in practice.
2. **No shuffled `train_test_split`.** Same problem.
3. **No directional accuracy without a baseline.** A 52% model on a market up 53% of days has zero edge. Always compare to the unconditional class frequency.
4. **No raw Sharpe without deflating it.** A Sharpe of 1.5 from a 100-trial sweep is ≈ Sharpe 0.5 in expectation. See `ml-hypothesis-design`.
5. **No ML metrics (AUC, F1) reported as trading metrics.** High AUC can still lose money when costs eat the marginal-profit trades.
6. **No single-fold / single-OOS evaluation.** One sample is one outcome from a distribution; you don't know the variance.

## Core Framework (summary)

Full detail, including the metric families and per-step rationale, lives in **`references/methodology.md`**.

1. **Pick the CV scheme that matches the data dependency structure.** Three families, increasing rigor: walk-forward (anchored vs rolling) → purged + embargoed K-fold (AFML Ch. 7) → Combinatorial Purged CV / CPCV (AFML Ch. 12, feeds PBO).
2. **Compute three metric families.** Classification (always vs the unconditional baseline), regression (OOS R² ≈ 0.005-0.05 for good models), and trading (Sharpe/Sortino/Calmar/MDD, **net-of-cost**). When classification and trading metrics disagree, trading wins.
3. **Compute PBO.** Probability the in-sample-best strategy underperforms the OOS median. PBO ≥ 0.5 = essentially random; PBO ≤ 0.05 is the conventional ship threshold. Owe PBO on any sweep.
4. **Report the full picture.** CV scheme + embargo/purge, all three metric families OOS, equity + drawdown curves, deflated Sharpe + PBO, per-regime performance, cost-sensitivity (0/1/5/10 bps). Feeds `tearsheet-generator`.

## Code Snippets

Minimal reference implementations (numpy/pandas/sklearn) for `PurgedKFold`, the walk-forward loop, `trading_metrics`, and PBO live in **`references/code-snippets.md`**. `mlfinlab` is the canonical production backbone; the snippets are for understanding and zero-dependency use.

## Common Pitfalls

The eight recurring failure modes (single-OOS-Sharpe-as-expectation, raw `KFold`, log-vs-simple Sharpe, ignoring costs, AUC≠profit, context-free Calmar, stopping at "passed CV", skipping PBO on a sweep) are detailed in **`references/methodology.md` → Common Pitfalls**.

## Sibling Skills (routing)

This skill owns financial-ML model **validation** — purged/combinatorial CV, PBO, deflated Sharpe, and the trading-vs-ML metric discipline. Hand off neighboring concerns:

| If the task is… | Use |
| --- | --- |
| Walk-forward EPOCH selection / overfitting-epoch control | `adaptive-wfo-epoch` |
| Pre-experiment power, trial-count, deflated-Sharpe *design* | `ml-hypothesis-design` |
| Leakage-safe feature pipeline / `t1` label end-times | `feature-engineering` |
| Tearsheet / MAE / optimal-leverage report (quantstats-rs) | `tearsheet-generator` |
| Compare results to an Optuna/Ray baseline; root-cause a discrepancy | `strategy-verify` |
| Actually run the backtest — vectorized authoring + sweeps | `vectorbt` |
| Actually run the backtest — event-driven engine / live | `nautilus-trader` |
| Port the strategy to another framework / Pine / Rust | `strategy-translator` |

## References

- **`references/methodology.md`** — full four-step framework (CV schemes, metric families, PBO recipe, reporting) + the eight common pitfalls.
- **`references/code-snippets.md`** — `PurgedKFold`, walk-forward loop, `trading_metrics`, PBO implementations.
- **`references/bibliography.md`** — libraries (`mlfinlab`, `scikit-learn`, `arch`, `quantstats`, …), academic papers (AFML, Bailey/López de Prado PBO + DSR, Hansen MCS/SPA, Lo, Harvey-Liu-Zhu), tutorials, and benchmark datasets. Last cross-checked 2026-05-20.
