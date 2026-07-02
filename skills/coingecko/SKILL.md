---
name: coingecko
version: 0.2.0
description: "CoinGecko REST API (v3) reference - crypto spot prices, market cap/volume, OHLC + historical market charts, coin/exchange/NFT metadata, trending, and onchain DEX/pool data (GeckoTerminal). Use when calling api.coingecko.com or pro-api.coingecko.com, picking an endpoint, wiring Demo vs Pro auth headers, or mapping coin/network/contract IDs. NOT for: trade execution or order placement (CoinGecko is read-only market data - use an exchange API); on-chain reads beyond price/pools (use an RPC/indexer); equities/FX/non-crypto data; the legacy pycoingecko wrapper internals; or other vendors' feeds (CoinMarketCap, CryptoCompare, Kaiko, exchange WebSockets)."
---

# CoinGecko API

Router for the CoinGecko v3 REST API. Pick the area below, then read the matching
file in `references/` for endpoint params, response shapes, and examples.

## Endpoints & auth (verify against references/authentication.md before coding)

- **Demo (free):** base `https://api.coingecko.com/api/v3/` — key via header
  `x-cg-demo-api-key: <KEY>` or query `x_cg_demo_api_key=<KEY>`.
- **Pro (paid):** base `https://pro-api.coingecko.com/api/v3/` — key via header
  `x-cg-pro-api-key: <KEY>` or query `x_cg_pro_api_key=<KEY>`.
- Demo and Pro keys are **not interchangeable** and each is valid only on its own
  base URL. `GET /ping` checks server status; `GET /key` reports Pro usage/credits.
- IDs are not symbols: use coin **id** (e.g. `bitcoin`, not `BTC`), `network` ids,
  and `asset_platform` ids. Resolve via the ID-map endpoints in `references/reference.md`.

## Route to the right reference

| You need… | Read |
|---|---|
| Auth, base URLs, rate limits, MCP server, getting started | `references/authentication.md`, `references/introduction.md` |
| Spot price (`/simple/price`), markets list (`/coins/markets`), coin detail, OHLC, historical `market_chart` | `references/coins.md`, `references/market_data.md` |
| Token price/info by contract address | `references/contract.md` |
| Exchanges, tickers, derivatives | `references/exchanges.md` |
| Trending coins/NFTs/categories, global stats | `references/trending.md` |
| NFT collection data | `references/nfts.md` |
| Onchain DEX/pools/trades (GeckoTerminal), `/onchain/...` | `references/other.md` |
| ID maps (coins/networks/asset platforms/currencies/entities), `/ping`, `/key` | `references/reference.md` |
| Plan tiers, pricing, no-code tutorials | `references/pricing.md` |
| Everything in one file (full dump) | `references/llms.md`, `references/llms-full.md` |

## Notes & gotchas

- Most endpoints cache 30–60s; historical `market_chart` granularity is auto-chosen
  by the requested day range (you can't force interval on Demo).
- `null` market caps appear for unverified onchain tokens — don't treat as zero.
- Pagination and some filters (e.g. `/pools/megafilter`, pages beyond 10) are Pro-only.
- CoinGecko also exposes an MCP server (`mcp.api.coingecko.com` / `mcp.pro-api...`);
  see `references/introduction.md`. For routed MCP access in this stack, see the
  `forge` and `mcp2cli` skills.

## Sibling skills

- Building/backtesting a strategy on this data → `strategy-translator`, `vectorbt`.
- Broad multi-source market research, not a single API → `deep-research`.
