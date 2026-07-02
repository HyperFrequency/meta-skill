# Risk, Backtesting & Portfolio

Coverage checklists for validation, risk, and allocation. Backtesting in this
ecosystem runs through `nautilus-trader` (event-driven, the source of truth) and
`vectorbt` (vectorized sweeps); tearsheets via `tearsheet-generator`.

## Risk management
- VaR calculation (see `value-at-risk`)
- Stress testing
- Scenario analysis
- Position sizing
- Stop-loss strategies
- Portfolio hedging
- Correlation analysis
- Drawdown control

## Risk analytics
- Value at Risk
- Conditional VaR (CVaR / expected shortfall)
- Stress scenarios
- Correlation breaks
- Tail risk analysis
- Liquidity risk
- Concentration risk
- Counterparty risk

## Backtesting framework
- Historical simulation
- Walk-forward analysis (see `adaptive-wfo-epoch`)
- Out-of-sample testing
- Transaction costs
- Slippage modeling
- Performance metrics
- Overfitting detection
- Robustness testing

Always model realistic costs and slippage. Treat in-sample Sharpe with suspicion —
overfit backtests (e.g. Sharpe-7) are a known failure mode; verify out-of-sample.

## Portfolio optimization
- Markowitz optimization
- Black-Litterman
- Risk parity
- Factor investing
- Dynamic allocation
- Constraint handling
- Multi-objective optimization
- Rebalancing strategies

## Model validation
- Cross-validation
- Out-of-sample testing
- Parameter stability
- Regime analysis (see `markov-regime-detection`)
- Sensitivity testing
- Monte Carlo validation
- Walk-forward optimization
- Live performance tracking

## Performance attribution
- Return decomposition
- Factor analysis
- Risk contribution
- Alpha generation
- Cost analysis
- Benchmark comparison
- Period analysis
- Strategy attribution
