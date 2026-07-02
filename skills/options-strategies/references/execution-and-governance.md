# Execution, Backtesting & Governance Reference

Operational detail for executing multi-leg options strategies on Alpaca, monitoring
risk, backtesting, and maintaining auditable compliance. Relocated here from SKILL.md
to keep the skill entry point lean.

> **SDK note (verified June 2026):** Use the modern **`alpaca-py`** SDK
> (`pip install alpaca-py`). The older `alpaca-trade-api-python` package is
> deprecated. Multi-leg options orders are submitted with
> `OrderClass.MLEG` and a `legs` list of `OptionLegRequest` objects — **not**
> `order_class='oto'` or `'bracket'`, which do not construct option spreads.

---

## 1. Multi-Leg Order Execution (alpaca-py)

Submit all legs of a spread atomically via a single `MarketOrderRequest` with
`order_class=OrderClass.MLEG`. Each leg is an `OptionLegRequest` carrying the OCC
option `symbol`, a `side` (`OrderSide.BUY`/`SELL`), and a `ratio_qty`.

```python
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, OptionLegRequest
from alpaca.trading.enums import OrderClass, OrderSide, TimeInForce

trade_client = TradingClient(api_key, secret_key, paper=True)

# Example: short iron condor (sell put spread + sell call spread)
order_legs = [
    OptionLegRequest(symbol=short_put_symbol,  side=OrderSide.SELL, ratio_qty=1),
    OptionLegRequest(symbol=long_put_symbol,   side=OrderSide.BUY,  ratio_qty=1),
    OptionLegRequest(symbol=short_call_symbol, side=OrderSide.SELL, ratio_qty=1),
    OptionLegRequest(symbol=long_call_symbol,  side=OrderSide.BUY,  ratio_qty=1),
]

req = MarketOrderRequest(
    qty=1,                          # number of spreads
    order_class=OrderClass.MLEG,
    time_in_force=TimeInForce.DAY,
    legs=order_legs,
)
res = trade_client.submit_order(req)
```

Discover tradable contracts with `GetOptionContractsRequest` (filter by
`underlying_symbols`, `expiration_date_gte/lte`, `strike_price_gte/lte`, `type`)
and `trade_client.get_option_contracts(req)`. Account must be approved for the
options trading level required by the strategy (Level 3 for undefined-risk legs).

## 2. Greeks Monitoring

Aggregate position Greeks across the book. Multiply per-contract Greeks by
`qty × 100` (the contract multiplier) and net long/short to get portfolio
delta/gamma/theta/vega. Drive hedging decisions from the aggregate, not per-leg.

## 3. Risk Controls

Implement a `RiskManager` that gates every order and runs continuously:

- `check_position_limits()` — reject if projected max loss exceeds the per-trade
  cap (e.g. 2% of capital).
- `check_portfolio_greeks()` — flag when aggregate |delta| breaches the neutrality
  band or net vega/theta exceeds limits.
- `adjust_delta_neutral()` — hedge residual delta with shares of the underlying.

## 4. Automated Exits

Set profit-target and stop-loss thresholds per position. For single-leg legs you
can attach bracket exits; for spreads, monitor net spread P/L and close the whole
`MLEG` position when `take_profit_pct` or `stop_loss_pct` is hit.

## 5. Historical Data & Backtesting

- Fetch historical option chains (e.g. via `yfinance` for prototyping, or Alpaca's
  historical options data API for fidelity).
- A `StrategyBacktester` runs the strategy over history, tracking trades and an
  equity curve, then computes: `total_trades`, `win_rate`, `avg_win`/`avg_loss`,
  `profit_factor`, `max_drawdown`, and Sharpe ratio.
- `optimize_strategy_parameters()` grid-searches parameter combinations with
  `itertools.product()` and ranks by Sharpe.

> For production-grade event-driven backtesting prefer the sibling
> **nautilus-trader** skill over a hand-rolled loop; use **vectorbt** for fast
> vectorized parameter sweeps.

## 6. Automated Deployment

An `AutomatedStrategyRunner` performs scheduled scans: for each symbol on the
watchlist it fetches market data, checks per-strategy entry conditions, builds the
`MLEG` order, submits it, and tracks the active position for exit/adjustment.

```python
def manage_positions(self):
    """Monitor and adjust active positions."""
    for strategy in self.active_strategies:
        if self._check_exit_conditions(strategy):
            self._close_strategy(strategy)
        elif self._check_adjustment_conditions(strategy):   # e.g. delta hedge
            self._adjust_strategy(strategy)
```

---

## 7. Governance, Compliance & Documentation

1. **Alpaca API compliance**
   - Adhere to the [Alpaca Terms of Service](https://alpaca.markets/legal/terms-of-service).
   - Respect rate limits (200 req/min trading, higher for market data) and
     implement exponential backoff.
   - Use appropriate auth scopes; clearly label paper-trading activity in logs.

2. **Security** — store credentials in environment variables, never in code:

   ```python
   import os
   from dotenv import load_dotenv

   load_dotenv()
   API_KEY_ID = os.getenv("ALPACA_API_KEY")
   API_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
   if not API_KEY_ID or not API_SECRET_KEY:
       raise ValueError("Alpaca API credentials not found in environment")
   ```

3. **Trade documentation** — record a full audit trail per trade: `trade_id`,
   strategy type, entry/exit timestamps and prices, entry Greeks and IV,
   underlying price, position size, max risk, expected vs. realized P/L, hold
   period, and exit reason. Persist to a database or CSV.

4. **Version control** — keep strategy code in Git, use semantic versioning for
   strategy iterations, document parameter changes in commits, and review before
   deploying new strategies.

5. **Performance reporting** — generate periodic reports summarizing trade counts,
   win rate, total/avg P/L, per-strategy breakdown, and risk metrics
   (max drawdown, Sharpe, profit factor).

6. **Educational/simulation labeling** — clearly mark paper-trading activity,
   include educational-purpose disclaimers, and separate production from testing
   environments.

---

## Risk Management Checklist

**Before every trade:**
- [ ] Calculate maximum loss; confirm it is acceptable
- [ ] Verify sufficient buying power / margin and options approval level
- [ ] Confirm expiration date and time-decay profile
- [ ] Check IV rank / percentile
- [ ] Review upcoming earnings or events
- [ ] Calculate breakeven points
- [ ] Set profit target and stop-loss levels

**During trade management:**
- [ ] Monitor aggregate portfolio Greeks daily
- [ ] Track P/L against maximum loss
- [ ] Adjust delta if it exceeds the neutrality threshold
- [ ] Roll positions approaching expiration
- [ ] Document adjustments with rationale

**Post-trade review:**
- [ ] Record actual P/L vs. expected
- [ ] Analyze what worked and what did not
- [ ] Update strategy parameters if warranted
- [ ] Document lessons learned

---

## Common Pitfalls & Mitigations

| Pitfall | Mitigation |
|---------|-----------|
| Over-leveraging undefined-risk strategies | Prefer defined-risk spreads; keep a margin buffer |
| Ignoring volatility regime changes | Monitor IV rank; switch strategy selection accordingly |
| Holding through expiration with no plan | Set reminders at 7/3/1 days before expiry; manage gamma risk |
| Chasing losses with bigger size | Enforce strict position sizing (e.g. max 2% capital/trade) |
| Neglecting transaction costs | Include commissions and slippage in backtests and P/L |
</content>
</invoke>
