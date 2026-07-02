---
title: vectorbt data loading
domain: trading
last_updated: 2026-06-29
---

# Data loading

Prefer VBT's `Data` loaders over yfinance directly — they cache,
reshape, and handle multi-symbol uniformly.

| Source | Class | Notes |
|---|---|---|
| Crypto (binance) | `vbt.BinanceData` | free, needs API key for high rate limits |
| Crypto (ccxt-backed) | `vbt.CCXTData` | 100+ exchanges via ccxt |
| US equities / ETFs | `vbt.YFData` | yfinance wrapper; cheap, inexact |
| Institutional | `vbt.PolygonData` (pro) | needs polygon.io API key |
| Alpaca | `vbt.AlpacaData` (pro) | needs alpaca creds |
| Local file | `vbt.HDFData` / `vbt.CSVData` / `vbt.ParquetData` | deterministic for reviewable backtests |

**For reviewable/reproducible backtests, prefer a cached local file.**
Live downloads drift; a frozen parquet does not. State the cache policy
in the first line of the emitted code as a comment.

```python
# cache policy: frozen parquet, no live download during review
data = vbt.ParquetData.pull("BTCUSDT.parquet")
close = data.get("Close")
```

Optional data-source keys consumed by the loaders:
`BINANCE_API_KEY` / `BINANCE_API_SECRET`, `POLYGON_API_KEY`,
`ALPACA_KEY_ID` / `ALPACA_SECRET_KEY`. The shakedown container sources
them from `$HOME/hyperfrequency/.env`.

Verify the exact loader signature against the live source (VBT Pro MCP
or Context7) before emitting — provider kwargs drift between releases.
