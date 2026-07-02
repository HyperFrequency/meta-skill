---
name: options-strategies
version: 0.2.0
description: "Design, model, and programmatically execute multi-leg options strategies (straddles, strangles, butterflies, vertical spreads, iron condors, calendars) on ALPACA MARKETS — payoff math, Greeks, IV analysis, multi-leg order submission, risk management, and backtesting. Tightly coupled to Alpaca's options API (alpaca-py SDK, OCC symbols, OrderClass.MLEG); execution examples assume an Alpaca account. WHEN: user wants to construct/price/backtest an options spread, pick a strategy from a market+volatility view, or place a multi-leg options order via Alpaca. NOT for: equity/futures/crypto spot trading (use ccxt/coingecko), generic backtesting frameworks (use nautilus-trader/vectorbt), single-stock forecasting (use the *-forecast skills), volatility-model fitting only (use garch-volatility), or brokers other than Alpaca (the execution layer would need rewriting)."
---

# Options Strategies (Alpaca)

Router for designing, modeling, and executing multi-leg options strategies on Alpaca
Markets infrastructure. **This skill is an entry point** — detailed math, code, and
reference tables live in `references/` and runnable code in `scripts/`. Load only the
file relevant to the current step.

> **Alpaca coupling:** strategy theory and payoff math are broker-agnostic, but the
> execution layer is bound to Alpaca's options API via the **`alpaca-py`** SDK
> (deprecated `alpaca-trade-api-python` is not used). Porting to another broker means
> rewriting the order-submission code. For framework-agnostic backtesting, delegate to
> the `nautilus-trader` or `vectorbt` sibling skills.

## Where to look

| Need | Go to |
|------|-------|
| Strategy structures, payoff formulas, examples, comparison matrix | `references/strategies.md` |
| Greeks definitions, formulas, interpretation | `references/greeks.md` |
| Historical/implied volatility, IV rank, expected move | `references/volatility.md` |
| Multi-leg execution, risk controls, backtesting, governance, checklists | `references/execution-and-governance.md` |
| Authoritative source catalog (Alpaca docs, OIC, CBOE, books) | `references/sources.md` |
| Black-Scholes pricing & Greeks code | `scripts/option_pricing.py` |
| Strategy construction / order-building code | `scripts/strategy_builder.py` |

## Workflow at a glance

1. **Setup** — Alpaca account + options approval, API keys in env vars, `pip install alpaca-py numpy pandas matplotlib scipy`. Credentials via environment only (see `references/execution-and-governance.md` §7).
2. **Select** — map market view + volatility view to a strategy (decision matrix below; full detail in `references/strategies.md`).
3. **Model** — price legs and compute Greeks (`scripts/option_pricing.py`, `references/greeks.md`); run payoff / Monte-Carlo simulation.
4. **Size & risk-check** — run the pre-trade checklist; confirm max loss, IV rank, events (`references/execution-and-governance.md`).
5. **Execute** — build legs and submit one `OrderClass.MLEG` order (`references/execution-and-governance.md` §1, `scripts/strategy_builder.py`).
6. **Manage** — monitor aggregate Greeks, P/L vs. max loss, exits/rolls.
7. **Backtest & govern** — backtest, optimize parameters, log an auditable trade record.

## Strategy decision matrix

| Strategy | Market View | Volatility View | Max Risk | Max Profit | Best When |
|----------|------------|-----------------|----------|------------|-----------|
| Long Straddle | Neutral | Expansion | Premium paid | Unlimited | Pre-earnings, major events |
| Long Strangle | Neutral | Expansion | Premium paid | Unlimited | Lower-cost volatility play |
| Iron Butterfly | Neutral | Contraction | Wing width − Premium | Premium received | High IV rank, range-bound |
| Calendar Spread | Neutral | Term-structure play | Net debit | Limited | Time-decay / term arbitrage |
| Bull Call Spread | Bullish | Neutral/Low | Net debit | Strike diff − Debit | Directional, limited capital |
| Bear Put Spread | Bearish | Neutral/Low | Net debit | Strike diff − Debit | Directional downside |
| Iron Condor | Range-bound | Contraction | Wing width − Premium | Premium received | Wide expected range, high IV |

Full structures, breakevens, Greek signatures, and worked examples: `references/strategies.md`.

## Related skills

- `garch-volatility`, `monte-carlo-simulation`, `value-at-risk` — volatility modeling and risk inputs that feed strategy selection.
- `nautilus-trader`, `vectorbt` — production / vectorized backtesting beyond the hand-rolled loop here.
- `strategy-translator` — port a strategy to/from other frameworks (Pine, Nautilus Rust, etc.).
- `ccxt`, `coingecko` — non-Alpaca / crypto execution and data.
- `tearsheet-generator` — performance reporting on backtest output.

---

*Educational and research use. Examples assume Alpaca's paper-trading environment.
Live options trading involves substantial risk and requires appropriate risk
management, capital allocation, and regulatory compliance.*
