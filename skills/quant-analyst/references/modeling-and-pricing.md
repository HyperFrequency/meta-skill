# Modeling, Pricing & Statistical Methods

Checklists for the research/modeling side of a quant engagement. These are
coverage prompts, not prescriptive APIs — pick what the strategy actually needs.

## Financial modeling
- Pricing models
- Risk models
- Portfolio optimization
- Factor models
- Volatility modeling
- Correlation analysis
- Scenario analysis
- Stress testing

## Statistical methods
- Time series analysis
- Regression models
- Machine learning (see sibling skills below)
- Bayesian inference
- Monte Carlo methods (see `monte-carlo-simulation`)
- Stochastic processes
- Cointegration tests
- GARCH models (see `garch-volatility`)

## Derivatives pricing
- Black-Scholes models
- Binomial trees
- Monte Carlo pricing
- American options
- Exotic derivatives
- Greeks calculation
- Volatility surfaces
- Credit derivatives

Options-specific work belongs to the `options-strategies` sibling.

## Machine learning applications
- Price prediction
- Pattern recognition
- Feature engineering (see `feature-engineering`)
- Ensemble methods
- Deep learning
- Reinforcement learning
- Natural language processing (see `sentiment-analysis-nlp`)
- Alternative data

Forecasting models have dedicated siblings (`lstm-forecast`, `transformer-forecast`,
`arima-forecast`, `prophet-forecast`, `xgboost`, `lightgbm`, `catboost`).

## Market data handling
- Data cleaning
- Normalization
- Feature extraction
- Missing data
- Survivorship bias
- Corporate actions
- Real-time processing
- Data storage

Sourcing/storage is owned by `neuro-quant-data-source-and-storage`,
`tardis-data-agent`, `ccxt`, `coingecko`.
