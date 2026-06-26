---
name: tardis-data-agent
description: >
  Agentic historical market data management via tardis.dev.
  Use for downloading, converting, validating, and front-filling
  crypto market data (trades, order book snapshots, funding rates,
  liquidations) across all exchanges. Supports interactive setup,
  rate-limit-aware pulls, priority groups, and daily front-fill.
version: "1.0.0"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Tardis Data Agent

Autonomous historical market data ingestion pipeline for crypto exchanges via [tardis.dev](https://tardis.dev).

## Overview

This skill manages the complete lifecycle of historical market data:
- **Interactive Setup**: Walks through API key config, exchange/symbol selection
- **Rate-Limit Aware**: Respects API rate limits, auto-backs off on 429s
- **Priority Groups**: User-configurable YAML pull schedule
- **Manifest Tracking**: Never re-downloads existing data
- **Daily Front-Fill**: Keeps data current automatically
- **Health Monitoring**: Detects gaps, missing files, venue inconsistencies
- **Parquet Conversion**: Raw CSV.gz → analysis-ready parquet

## Quick Start

### 1. Configure API Key

Ensure `TARDIS_API_KEY` is set in `.env`:
```bash
echo "TARDIS_API_KEY=TD.your_key_here" >> .env
```

### 2. Edit Pull Schedule

Edit `configs/tardis_schedule.yaml` to define what data to download:
- **Groups**: Named collections of exchanges + symbols + data types
- **Priority**: Groups are pulled in priority order (1 = first)
- **Date Ranges**: Per-group start/end dates

### 3. Run Downloads

```bash
# Activate the environment
source ~/swarm_main_env/bin/activate

# Dry run (preview what will be downloaded)
python -m src.data.tardis_agent --group core-futures-tick --dry-run

# Download a specific group
python -m src.data.tardis_agent --group core-futures-tick

# Download all groups
python -m src.data.tardis_agent --all

# Front-fill to latest available date
python -m src.data.tardis_agent --frontfill
```

### 4. Convert to Parquet

```bash
python -m src.data.tardis_agent --convert
```

### 5. Check Status

```bash
python -m src.data.tardis_agent --status
python -m src.data.tardis_agent --validate
```

## Data Types Available

| Type | Tardis Channel | Content |
|------|---------------|---------|
| Trades | `trades` | Every fill: price, size, side, timestamp |
| OB Snapshots | `book_snapshot_25` | Full 25-level bid/ask state |
| OB Updates | `incremental_book_L2` | Delta updates for real-time reconstruction |
| Funding | `derivative_ticker` | Funding rate, OI, mark price, index price |
| Liquidations | `liquidations` | Forced closures with size and side |
| Book Ticker | `book_ticker` | Best bid/ask updates |

## Supported Exchanges

All exchanges from tardis.dev Pro subscription:
- **Futures**: binance-futures, bybit, hyperliquid, okex-swap, deribit, gate-io-futures, bitget-futures, kucoin-futures
- **Spot**: binance, bybit-spot, coinbase, kraken, bitstamp, gemini, gate-io
- **Options**: deribit, binance-options, okex-options, bybit-options

## File Structure

```
data-historical/
├── tardis/                      # Raw tardis downloads (gzipped CSV)
│   ├── binance-futures/
│   │   ├── trades/              # {exchange}_trades_{date}_{symbol}.csv.gz
│   │   ├── book_snapshot_25/
│   │   ├── derivative_ticker/
│   │   └── liquidations/
│   ├── bybit/
│   └── hyperliquid/
├── parquet/                     # Converted analysis-ready data
│   ├── ohlcv/{exchange}/        # {symbol}_{timeframe}.parquet
│   ├── l2book/{exchange}/       # {symbol}_book_snapshot_25.parquet
│   ├── trades/{exchange}/
│   ├── funding/{exchange}/      # {symbol}_funding.parquet
│   └── liquidations/{exchange}/
├── features/                    # Feature pipeline output
└── manifests/
    └── download_log.jsonl       # Append-only download tracking
```

## Agent Management Operations

### Rate Limit Management
- On initial setup, quantifies rate limits from API response headers
- Adjusts concurrency based on subscription tier (trial vs pro)
- Exponential backoff on failures, 60s cooldown on 429s
- Configurable via `configs/tardis_schedule.yaml` → `rate_limits`

### Priority-Based Pull Groups
- Groups execute in priority order (1 = highest)
- Each group defines: exchanges, symbols, data types, date range, concurrency
- User-selectable granularity: full tick data vs trades-only vs snapshots-only

### Routine Upkeep
- **Daily front-fill**: `--frontfill` fills from latest downloaded date to yesterday
- **Failure notification**: Logged via `src/production/alert_manager.py`
- **Venue inconsistency**: Detected during `--validate` (missing symbols, truncated files)
- **Endpoint failure**: Retry with backoff, then alert

### Connections
- **tardis.dev API**: CSV dataset downloads via `tardis-dev` Python client
- **MCP Internal**: Exposed as `tardis-data-agent` MCP server for Aden/OpenClaw
- **Feature Pipeline**: Output parquet consumed by `src/features/pipeline.py`

### File Structure Management
- User dictates structure via YAML config
- Organized by: exchange → data type → date/symbol
- Parquet output organized by: data classification → exchange → symbol
