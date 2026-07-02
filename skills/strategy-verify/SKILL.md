---
name: strategy-verify
description: >
  Compares a backtest's results against Optuna/Ray optimization baselines and
  root-causes trading-logic discrepancies: trade-by-trade entry/exit/PnL
  matching, equity-curve correlation/RMSE/deviation checks, and analysis of why
  two runs diverge. Trigger even without the word "verify" on phrases like
  "compare this backtest to my optuna baseline", "does my backtest match the
  optimization", "why don't my live trades match the backtest", or "root-cause
  this Sharpe/PnL discrepancy". For vectorized backtest authoring / parameter
  sweeps use vectorbt; for the event-driven engine + live/Hyperliquid deployment
  use nautilus-trader; for porting to Rust/Pine/another framework use
  strategy-translator; for walk-forward epoch selection use adaptive-wfo-epoch;
  for "is this Sharpe real / PBO / purged CV" validation use model-evaluation;
  for tearsheets / MAE / leverage use tearsheet-generator (quantstats-rs); for
  distributed Optuna/Ray HPO infra use neuro-quant-distributed-optimization.
version: "1.0.0"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
license: LGPL-3.0 (nautilus_trader), MIT (optuna), Apache-2.0 (ray), BSD-3-Clause (pandas/numpy)
metadata:
    skill-author: HyperFrequency
    skill-domain: trading
---

# Strategy Verification Skill

## What This Skill Does

This skill provides comprehensive strategy verification to ensure trading logic consistency between optimization and deployment:

- **Trade Comparison**: Validates that entry prices, exit prices, and PnL match within tolerance
- **Equity Curve Analysis**: Compares equity curves using correlation, RMSE, and deviation metrics
- **Root Cause Analysis**: Uses Claude's UltraThink mode for deep reasoning about discrepancies
- **Automated Recommendations**: Provides specific fixes for each issue found
- **Nautilus Integration**: Runs verification through nautilus_trader backtest engine

## When to Use This Skill

Use this skill when:

1. You optimized a strategy with Optuna or Ray and want to confirm a re-run with the same config reproduces the same trades and equity curve.
2. Your deployed/live PnL diverges from the optimization baseline and you need to root-cause the cause (fees, slippage, sizing, data, seed).
3. You need a pass/fail gate before deploying — entry prices, exit prices, and PnL within tolerance of the baseline.
4. You suspect an implementation bug between the optimizer's model of the strategy and the actual backtest engine.
5. You want a CI/CD check that fails the build when verification does not match the stored baseline.
6. You need an equity-curve reconciliation (correlation / RMSE / max + mean deviation) between two runs of the "same" strategy.

## Required Tooling

This is a local Python pipeline — it does not depend on an MCP server. If you need to drive an MCP tool (e.g. to fetch optimization artifacts from infra), route through `/forge` or `mcp2cli`; never open a raw SSE connection.

| Dependency | Purpose | Route / sibling |
|------------|---------|-----------------|
| Python 3.10+ (`pandas`, `numpy`) | Load baselines, compute trade/equity deltas | local |
| `nautilus_trader` (optional) | Re-run the verification backtest; falls back to simulation | engine details → `nautilus-trader` |
| Optuna / Ray baseline artifacts | Source-of-truth metrics to compare against | produced by `neuro-quant-distributed-optimization` |

## Prerequisites

- Python 3.10+ with pandas, numpy
- Nautilus Trader (optional, falls back to simulation)
- Optimization baseline results (from Optuna/Ray)
- Strategy config.json to verify

## Quick Start

```bash
# Basic verification
python3 $HOME/Desktop/Dev/scripts/strategy_verify.py \
  /path/to/config.json \
  /path/to/optimization/baseline/

# With verbose output and JSON
python3 $HOME/Desktop/Dev/scripts/strategy_verify.py \
  ./config.json ./baseline/ \
  --verbose --json
```

Or use the command:
```bash
/strategy-verify ./config.json ./baseline/
```

---

## Full Guide

The complete verification process, tolerance tables, baseline/output file layouts,
common discrepancy causes + fixes, CI/CD + batch examples, troubleshooting, exit
codes, best practices, and the `StrategyVerifier` API reference live in
[`references/guide.md`](references/guide.md). Key facts to know up front:

- **Pipeline**: load baseline → re-run backtest (nautilus, or simulation fallback) → compare trades + equity → UltraThink root-cause on any mismatch.
- **Default tolerances**: PnL 0.1%, entry/exit price 0.01%, final equity 1%, equity-curve correlation ≥ 0.99.
- **Baseline folder** needs `config.json` plus `trades.{parquet,csv}` and `results.parquet`/`equity_curve.csv`; `metrics.json` and `monte_carlo.json` are optional.
- **Exit codes**: 0 passed, 1 failed/warning, 2 error — wire these into CI gates.
- **First suspects** when runs diverge: date range, fee/slippage config, position sizing, initial capital, random seed.

## Anti-Patterns

- **Deploying without verifying.** Skipping the gate defeats the purpose — a passing optimization is not a passing deployment.
- **Comparing runs on different data.** Exchange, symbol, date range, and bar resolution must match exactly, or every downstream delta is noise.
- **Ignoring fee/slippage config drift.** Fee and slippage differences dominate PnL deltas; reconcile them before chasing exotic causes.
- **Authoring or sweeping a backtest here.** Building the backtest or running parameter sweeps is `vectorbt`; running the live/event-driven engine is `nautilus-trader`. This skill only *reconciles* their output against the baseline.
- **Treating "verification passed" as "the edge is real."** Reproducibility is not statistical validity — PBO, purged/embargoed CV, and deflated Sharpe live in `model-evaluation`.

## Sibling Skills (Routing)

| Need | Use |
|------|-----|
| Vectorized backtest authoring / parameter sweeps / IndicatorFactory | `vectorbt` |
| Event-driven backtest engine + live / Hyperliquid deployment | `nautilus-trader` |
| Port / translate a strategy to Rust / Pine / another framework | `strategy-translator` |
| Walk-forward epoch / WFE / overfitting-epoch control | `adaptive-wfo-epoch` |
| "Is this Sharpe real" / PBO / purged + embargoed CV / deflated Sharpe | `model-evaluation` |
| Tearsheet / MAE / optimal-leverage (quantstats-rs) | `tearsheet-generator` |
| Distributed Optuna / Ray / Dask HPO infra + storage / fan-out | `neuro-quant-distributed-optimization` |

## References

- nautilus_trader — https://nautilustrader.io/docs/ (LGPL-3.0)
- Optuna — https://optuna.readthedocs.io/ (MIT)
- Ray Tune — https://docs.ray.io/en/latest/tune/ (Apache-2.0)
- pandas — https://pandas.pydata.org/docs/ (BSD-3-Clause)

License: LGPL-3.0 (nautilus_trader), MIT (optuna), Apache-2.0 (ray), BSD-3-Clause (pandas/numpy). Original skill contributions © HyperFrequency.

Last cross-checked: 2026-06-27.
