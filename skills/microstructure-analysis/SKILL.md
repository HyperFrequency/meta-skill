---
name: microstructure-analysis
version: 0.1.0
description: Order-book microstructure analysis for short-horizon alpha and execution. Use when working with limit order book data, computing order flow imbalance (OFI), VPIN, queue position, or footprint reads; classifying trade direction (tick rule, Lee-Ready); estimating toxic flow via Kyle's lambda; or reasoning about how trades move prices on microsecond-to-minute horizons. Triggers on phrases like "order book imbalance", "VPIN", "footprint", "tick rule", "buy/sell classification", "Kyle's lambda", "toxic flow", "queue position", or "L2/L3 data". For backtest-level position sizing use vectorbt; for live execution use nautilus-trader; for general feature engineering use feature-engineering. Not for daily-bar momentum or value strategies where microstructure features are noise, or pure portfolio construction abstracted by an execution layer.
allowed-tools: Read Write Edit Bash
---

# Order Book Microstructure Analysis

## Overview

Microstructure is what happens between the candles. At the bar level, a price moved from 100.00 to 100.05; at the microstructure level, that move was the cumulative outcome of cancellations, insertions, and aggressive trades that swept through resting liquidity. The two views are not interchangeable, and most quant ML failures at high frequency come from treating them as if they were.

This skill is the conceptual framework — the *why* and the *when*. It covers how to classify trades when you only see prices, how to measure order-flow imbalance, how to detect toxic flow, and how to read a footprint chart without storytelling. Operational implementations live in libraries (`mlfinlab`, `nautilus_trader`).

This SKILL.md is a router. Detail lives in `references/`:

- **`references/core-framework.md`** — full layer-by-layer treatment of the five framework layers below.
- **`references/code-snippets.md`** — runnable reference implementations of Lee-Ready, OFI, VPIN, and Kyle's lambda.
- **`references/bibliography.md`** — libraries, deep-dive docs, academic papers, tutorials, and standard datasets.

## When to Use This Skill

Use this skill when:

- Building short-horizon alpha (minutes or less) where bar-level OHLC features are too coarse
- Designing execution algorithms and need to estimate impact, slippage, or adverse selection
- You have tick or L2 data and don't know whether the marginal trade was buyer- or seller-initiated
- A long-horizon strategy is being eaten by execution costs and you need to diagnose where
- Auditing why a backtest's fills don't match live fills (queue position, latency, hidden liquidity)
- Constructing features for an ML model that consumes order-book state

Do **not** use this for: daily-bar momentum or value strategies (microstructure features will be noise at that horizon); or pure portfolio construction where the trade dynamics are already abstracted by an execution layer.

## Core Framework (router)

The framework is layered — each layer answers a different question and consumes a different data type. Summaries below; full reasoning in `references/core-framework.md`.

1. **Trade classification** (ticks, no book) — infer whether each trade was buyer- or seller-initiated. **Tick rule** (vs previous trade price) or **Lee-Ready** (vs prevailing midpoint, tick rule at the mid). EMO/BVC are alternatives; BVC works on OHLCV bars. Foundation for everything else.
2. **Order-flow imbalance** (L1/L2) — **OFI** (Cont-Kukanov-Stoikov 2014) measures *net change* in top-of-book liquidity (a flow, not a snapshot); strong contemporaneous predictor of second-to-minute returns. Distinguish from **static book imbalance** `(bid_size - ask_size)/(bid_size + ask_size)`, a weak baseline feature.
3. **Toxic flow** — **Kyle's lambda** (1985): OLS slope of returns on signed volume = price impact / cost-of-immediacy. **VPIN** (Easley-López de Prado-O'Hara 2012): one-sidedness over equal-volume buckets; a regime/throttle indicator, weak as directional alpha.
4. **Footprint reading** — per-level buy vs sell volume within a bar: imbalance rows, absorption, exhaustion. Treat as candidate hypotheses, not signals; backtest with triple-barrier labeling.
5. **Queue position** — fill probability for passive orders depends on queue rank, not observable from L2. Use pessimistic (back-of-queue), L3/MBO (exact, e.g. Databento), or cancellation-aware FIFO estimates. Ignoring it overstates fill rates 2-5×.

## Common Pitfalls

1. **Using the tick rule on data with reporting lag.** If trade timestamps lead quote timestamps (common in venue feeds), the "current quote" hasn't been observed yet and tick-rule signs invert. Validate against a venue that publishes signed trades or trades-with-aggressor data.
2. **Confusing static book imbalance with OFI.** Static imbalance at time t is a snapshot; OFI is a flow integral. They diverge in regimes like queue-build-up (large static imbalance, low OFI) vs sweep (low static imbalance after, large OFI during).
3. **Backtesting microstructure signals with bar-aligned labels.** A 1-minute bar return doesn't reflect a 200ms signal. Use event-based labeling (triple-barrier in `feature-engineering`) on tick or near-tick timescales.
4. **Assuming queue position is FIFO and you start at the back.** Some venues use pro-rata, price-time-pro-rata hybrids, or hidden-order priority. Read the venue docs; FIFO assumptions on a pro-rata venue are systematically wrong.
5. **Treating VPIN as alpha.** VPIN is a regime/toxicity indicator — useful for sizing down or stepping out, not as a directional signal on the asset.
6. **Ignoring iceberg / hidden orders.** L2 size shows only displayed depth; hidden liquidity fills aggressive orders without appearing in snapshots. Footprint analyses that ignore this overstate true imbalance.
7. **Mismatching trade and quote clocks.** Exchange, gateway, and capture timestamps can disagree by ms to seconds. Pick one canonical clock and document it; don't silently mix.

## Tooling and Sibling Skills

Operationalize this methodology with:

- **`nautilus-trader`** — L2/L3 deltas via `subscribe_order_book_deltas`, built-in `OrderBookImbalance` strategy; canonical live execution layer.
- **`tardis-data-agent`** — historical L2/L3 tick and book data across crypto venues; feeds the OFI and VPIN snippets.
- **`mlfinlab`** (library) — reference implementations of VPIN, volume/dollar bars, and Kyle's/Amihud's/Hasbrouck's lambda. `pip install mlfinlab`.
- **`feature-engineering`** (sister) — leakage-safe ML feature matrix + triple-barrier labeling for tick-rate signals.
- **`model-evaluation`** (sister) — purged + embargoed CV that microstructure ML demands.
- **`vectorbt`** — bar-level backtests incorporating microstructure-derived features.
- **`ml-hypothesis-design`** (sister) — microstructure backtests burn trial budgets fast; deflate accordingly.

Full library docs, papers, and datasets: `references/bibliography.md` (last cross-checked 2026-05-20).
