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

## Complete Guide

### Understanding Strategy Verification

When you optimize a strategy with Optuna or Ray, you get a set of parameters and expected performance metrics. This skill verifies that:

1. **Same inputs → Same outputs**: Running the strategy with the same config produces identical trades
2. **No implementation bugs**: The strategy logic is correctly implemented
3. **Data consistency**: The same market data is used
4. **Fee accuracy**: Fee calculations match between optimization and verification

### Verification Process

#### Step 1: Load Baseline Results

The skill loads your optimization baseline from:
- `config.json` - Strategy parameters
- `trades.parquet` or `trades.csv` - Trade history
- `results.parquet` or `equity_curve.csv` - Equity curve data
- `metrics.json` - Performance metrics

#### Step 2: Run Verification Backtest

Executes the strategy configuration through nautilus_trader (or simulation mode if unavailable) to generate:
- Verification trade list
- Verification equity curve

#### Step 3: Compare Results

Compares baseline and verification results:

**Trade Matching (0.1% tolerance)**:
- Entry prices (0.01% tolerance)
- Exit prices (0.01% tolerance)
- PnL amounts (0.1% tolerance)
- Trade count and ordering

**Equity Curve Matching**:
- Correlation (minimum 0.99)
- RMSE calculation
- Maximum deviation percentage
- Mean deviation percentage
- Final value comparison (1% tolerance)

#### Step 4: UltraThink Analysis

When discrepancies are found, Claude's extended thinking mode analyzes:

1. **Root Cause Identification**
   - Parameter differences
   - Floating point precision issues
   - Timing/order execution differences
   - Data source inconsistencies
   - Random seed differences
   - Fee calculation differences
   - Indicator calculation differences

2. **Specific Fixes**
   - Code changes needed
   - Configuration adjustments
   - Data corrections

3. **Validation Steps**
   - How to confirm the fix works
   - Regression testing recommendations

### Tolerance Configuration

Default tolerances (adjustable in code):

| Metric | Tolerance | Description |
|--------|-----------|-------------|
| PnL | 0.1% | Per-trade profit/loss |
| Price | 0.01% | Entry/exit prices |
| Equity | 1% | Final equity value |
| Correlation | 0.99 | Minimum curve correlation |

### Baseline Folder Structure

Your optimization baseline folder should contain:

```
optimization_results/
├── config.json          # Strategy parameters
├── metrics.json         # Performance metrics (optional)
├── trades.parquet       # Trade history (or trades.csv)
├── results.parquet      # Equity curve (or equity_curve.csv)
└── monte_carlo.json     # Monte Carlo results (optional)
```

### Output Files

Verification produces:

```
{strategy}_verification_{timestamp}.json
```

Contains:
- Overall status (PASSED/FAILED/WARNING/ERROR)
- Trade-by-trade comparison
- Equity curve comparison metrics
- All discrepancies found
- Root cause analysis (from UltraThink)
- Recommendations for fixing issues

### UltraThink Mode

This skill ALWAYS uses extended thinking for analysis. The thinking process:

1. **Deep Reasoning**: Claude analyzes all discrepancies systematically
2. **Pattern Recognition**: Identifies common issue patterns
3. **Causal Analysis**: Traces discrepancies to specific causes
4. **Solution Generation**: Proposes concrete fixes

To disable UltraThink (not recommended):
```bash
python3 strategy_verify.py config.json baseline/ --no-ultrathink
```

### Common Discrepancy Causes

#### Trade Count Mismatch
**Symptom**: Different number of trades
**Causes**:
- Different date ranges
- Signal generation timing differences
- Stop-loss/take-profit trigger differences
- Missing data in one source

**Fix**: Verify date ranges match exactly, check signal logic

#### Entry Price Mismatch
**Symptom**: Entry prices differ by > 0.01%
**Causes**:
- Slippage calculations differ
- Order type differences (market vs limit)
- Price source differences (open/close/OHLC)

**Fix**: Verify order execution logic, check price source

#### PnL Mismatch
**Symptom**: Profit/loss differs by > 0.1%
**Causes**:
- Fee calculation differences
- Position sizing differences
- Leverage calculation differences

**Fix**: Compare fee structures, verify position sizing

#### Equity Curve Deviation
**Symptom**: Correlation < 0.99 or deviation > 1%
**Causes**:
- Cumulative PnL differences
- Different initial capital
- Different compounding logic

**Fix**: Check cumulative calculations, verify initial capital

### Integration Examples

#### Deployment Workflow

```python
# 1. Optimize strategy
python optimize_strategy.py --token SOL --trials 500

# 2. Verify best result
python strategy_verify.py \
  ./optimizations/SOL/best_returns/config.json \
  ./optimizations/SOL/best_returns/

# 3. Only deploy if passed
if verification_passed:
    deploy_strategy(config)
```

#### CI/CD Integration

```yaml
verify-strategy:
  stage: test
  script:
    - python strategy_verify.py $CONFIG $BASELINE --json > verify.json
    - |
      status=$(jq -r '.status' verify.json)
      if [ "$status" != "passed" ]; then
        echo "Strategy verification failed"
        exit 1
      fi
```

#### Batch Verification

```bash
# Verify all optimized strategies
for dir in $HOME/Desktop/Dev/Backtests/optimizations/*/best_*; do
  echo "Verifying $dir..."
  python strategy_verify.py "$dir/config.json" "$dir" --json
done
```

### Troubleshooting

#### Nautilus Not Available

```
WARNING: Nautilus Trader not available, using simulation mode
```

**Solution**: Install nautilus_trader or run in simulation mode for logic testing only

#### Empty Trade List

```
ERROR: No trades file found in baseline
```

**Solution**: Ensure trades.parquet or trades.csv exists in baseline folder

#### Analysis Timeout

```
Analysis timed out after 5 minutes
```

**Solution**: Reduce complexity or run with `--no-ultrathink` for basic analysis

### Performance Metrics

| Operation | Typical Time |
|-----------|--------------|
| Load baseline | < 100ms |
| Run backtest | 1-30s (depends on data) |
| Compare trades | < 500ms |
| UltraThink analysis | 30s-5min |
| Save results | < 100ms |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Verification passed |
| 1 | Verification failed or warning |
| 2 | Error during verification |

### Related Commands

- `/generate-tearsheet` - Generate performance tearsheet from trades
- `/sparc tdd` - TDD workflow for strategy development
- `/verify check` - General code verification
- `npx claude-flow@alpha truth` - View verification metrics

### Best Practices

1. **Always verify before deployment** - Never skip verification
2. **Use identical data** - Same exchange, same date range
3. **Check fee structures** - Fees significantly impact PnL
4. **Keep baselines versioned** - Store optimization results in git
5. **Run periodically** - Re-verify after code changes
6. **Review UltraThink analysis** - Don't just trust pass/fail
7. **Document fixes** - Track what caused discrepancies

### API Reference

```python
from strategy_verify import StrategyVerifier, VerificationResult

verifier = StrategyVerifier(
    config_path="/path/to/config.json",
    baseline_path="/path/to/baseline/",
    data_path="$HOME/Desktop/Dev/DATA",
    output_path="$HOME/Desktop/Dev/Backtests/results",
    use_ultrathink=True
)

result: VerificationResult = await verifier.verify()

print(f"Status: {result.status.value}")
print(f"Trades match: {result.trades_match}")
print(f"Equity match: {result.equity_match}")
print(f"Recommendations: {result.recommendations}")
```

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
