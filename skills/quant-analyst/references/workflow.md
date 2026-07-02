# Quant Workflow

Systematic phases for a quant engagement. Use as a spine; not every task needs
every phase.

## Inputs to gather first
Before modeling, establish the engagement parameters with the user (do not assume
a "context manager" provides them): asset classes, trading frequency, risk
tolerance, capital allocation, regulatory constraints, performance targets, and
the available historical/market data.

## 1. Strategy analysis
Research and design the strategy.
- Market research, data analysis, pattern identification
- Model selection, risk assessment
- Backtest design, performance targets, implementation planning
- Study inefficiencies, test hypotheses, validate patterns, document findings

## 2. Implementation
Build and test the models.
- Model development, strategy coding
- Backtest execution (nautilus-trader / vectorbt), parameter optimization
- Risk controls, live/paper testing, performance monitoring
- Patterns: rigorous testing, conservative assumptions, robust validation,
  version control, documentation

## 3. Delivery
Deploy validated systems.
- Models validated, performance verified out-of-sample, risks controlled
- Compliance met, monitoring active, documentation complete
- Report results honestly: state the backtest window, costs/slippage assumptions,
  and out-of-sample vs in-sample metrics. Do not headline an in-sample Sharpe.

## Research process
Literature review → data exploration → hypothesis testing → model development →
validation → documentation → peer review → continuous monitoring.

## Progress / result reporting shape
A compact JSON status is a useful convention when reporting to an orchestrator:
```json
{
  "agent": "quant-analyst",
  "status": "developing",
  "progress": {
    "sharpe_ratio": 1.4,
    "max_drawdown": "12%",
    "win_rate": "55%",
    "backtest_years": 10,
    "out_of_sample": true
  }
}
```
Numbers here are illustrative placeholders — fill with real measured values and
flag whether they are in-sample or out-of-sample.
