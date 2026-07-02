---
name: ccxt
version: 0.2.0
description: "Unified API for connecting to 100+ cryptocurrency exchanges (Binance, OKX, Bybit, Coinbase, Kraken...) in JavaScript/TypeScript, Python, PHP, and C#. Use for fetching market data (tickers, OHLCV, order books, trades), placing/managing orders, querying balances and positions, and building crypto trading bots against live exchange REST/WebSocket APIs. CCXT Pro adds WebSocket streaming (watch* methods). Use WHEN you need to talk to a real exchange's API with a single unified interface. Do NOT use for: backtesting or strategy execution engines (use nautilus-trader or vectorbt), non-exchange aggregated market data / coin metadata (use coingecko), historical tick archives (use tardis-data-agent), or anything outside crypto exchange connectivity."
---

# CCXT

Router for working with the CCXT cryptocurrency exchange-trading library. CCXT normalizes the wildly inconsistent APIs of 100+ exchanges behind one unified interface (symbols, market structures, order/balance/ticker schemas) across JS/TS, Python, PHP, and C#.

## When to use

- Connecting to a crypto exchange's REST or WebSocket API (auth, rate limiting, signing).
- Fetching market data: `fetchTicker`, `fetchOHLCV`, `fetchOrderBook`, `fetchTrades`, `fetchFundingRate`.
- Trading: `createOrder`, `cancelOrder`, `fetchOrder(s)`, `fetchBalance`, `fetchPositions`.
- Real-time streaming via CCXT Pro `watch*` methods (`watchTicker`, `watchOHLCV`, `watchOrders`).
- Probing exchange capabilities via `exchange.has[...]` and the `.features` property.

## When NOT to use (route elsewhere)

- **Backtesting / live strategy engines** → `nautilus-trader`, `vectorbt`. CCXT is a connectivity layer, not a trading engine.
- **Aggregated coin metadata, prices, market caps** (not tied to one exchange's API) → `coingecko`.
- **Bulk historical tick / L2 data archives** → `tardis-data-agent`.
- **Porting a strategy between frameworks** → `strategy-translator`.

## Core mental model

1. **Instantiate** an exchange class: `new ccxt.binance({ apiKey, secret })` / `ccxt.binance({...})`. For async Python use `import ccxt.async_support as ccxt`.
2. **`loadMarkets()`** first — populates symbols, precision, limits, and `contractSize` (required for swaps/futures sizing).
3. **Check capability** before calling: `if (exchange.has['fetchOHLCV']) {...}`. `exchange.has` and `.features` describe what each exchange supports.
4. **Enable rate limiting**: `enableRateLimit: true` (default true) to avoid bans.
5. Use **unified params** for cross-exchange code; drop to exchange-specific implicit API methods only when unified coverage is missing.

## Quick reference (unified method signatures)

```javascript
// REST
fetchTicker (symbol, params = {})
fetchOHLCV  (symbol, timeframe = '1m', since = undefined, limit = undefined, params = {})
fetchOrderBook (symbol, limit = undefined, params = {})
fetchBalance (params = {})
createOrder (symbol, type, side, amount, price = undefined, params = {})
cancelOrder (id, symbol = undefined, params = {})

// CCXT Pro (WebSocket) — same schemas, prefixed watch*
watchTicker (symbol, params = {})
watchOHLCV  (symbol, timeframe, since, limit, params = {})
watchOrders (symbol, since, limit, params = {})
```

Minimal Python example:

```python
import ccxt
exchange = ccxt.binance()
exchange.load_markets()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h')   # [[ts, o, h, l, c, v], ...]
```

## Common gotchas

- **Market-buy with cost**: many exchanges price spot market-buys in the *quote* currency. Check `exchange.has['createMarketBuyOrderWithCost']` / the `createMarketBuyOrderRequiresPrice` option. See `references/faq.md`.
- **Swaps/futures sizing** trades *contracts*, not base currency — multiply by `market['contractSize']`. See `references/faq.md`.
- **`reduceOnly`** is passed via `params={'reduceOnly': True}` to `createOrder`.
- **Funding rates**: distinguish `previousFundingRate` / `fundingRate` (upcoming) / `nextFundingRate`. See `references/faq.md`.
- **Debugging**: set `exchange.verbose = True` to dump raw request/response before reporting any issue.

## Reference files (`references/`)

Load these on demand — do not inline them:

- **manual.md** — the full CCXT manual (unified API, market/order/trade structures, params). Primary deep reference.
- **faq.md** — common how-tos (market-buy cost, reduceOnly, takeProfit/stopLoss, spot vs swap, funding rates, issue-reporting checklist).
- **getting_started.md** — install (npm / pip / composer / NuGet), custom browser builds, proxy setup.
- **pro.md** — CCXT Pro WebSocket streaming overview.
- **specification.md** — unified data-structure specification.
- **exchanges.md** — supported exchanges and per-exchange capability notes.
- **cli.md** — CCXT CLI usage.
- **index.md** — index of all reference categories.

## Notes

- Method names are camelCase in JS/TS/PHP/C# and snake_case in Python (`fetchOHLCV` ↔ `fetch_ohlcv`).
- Never commit `apiKey`/`secret`; load from env or a gitignored keys file.
