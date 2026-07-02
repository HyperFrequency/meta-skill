# Core framework — full detail

The framework is layered. Each layer answers a different question and consumes a
different data type. `SKILL.md` carries the one-line summary of each layer; this
file is the expanded reasoning.

## Layer 1 — Trade classification (you have ticks but no book)

When you only see (time, price, size) ticks, you must infer whether each trade was
buyer-initiated (aggressor lifted the offer) or seller-initiated (aggressor hit the
bid). This is the foundation for everything that follows.

**Tick rule.** Compare the trade price to the previous *trade* price. Up-tick →
buyer-initiated; down-tick → seller-initiated; zero-tick → carry the previous sign.
Simple, no quote data needed, but noisier than quote-based methods.

**Lee-Ready algorithm** (Lee & Ready 1991). Compare the trade price to the prevailing
*midpoint quote*. Above midpoint → buyer-initiated; below → seller-initiated; at
midpoint → use the tick rule. The classical paper recommends a 5-second lag on the
quote to handle reporting delays in 1990s NYSE data; modern electronic markets often
need a much smaller lag (or none). Validate against trades-with-side data on your
venue if available.

**EMO/BVC alternatives.** Ellis-Michaely-O'Hara and Bulk-Volume Classification exist;
BVC is useful when you only have OHLCV bars, not ticks.

## Layer 2 — Order-flow imbalance (you have L1 or L2)

**Order Flow Imbalance (OFI)** in the Cont-Kukanov-Stoikov (2014) formulation measures
the *net change* in bid and ask liquidity at the top of the book over a time window.
It is not the difference in resting size — it is the difference in *flow*. The recipe:

For each book update at time t:
- If best bid price went up, or stayed same with bid size increased → contribute +Δbid_size
- If best bid price went down, or stayed same with bid size decreased → contribute -Δbid_size
- Symmetric on the ask side, with sign flipped (ask flow is the opposite direction)

Sum across the window. OFI is a strong contemporaneous predictor of price change at the
second-to-minute horizon; the Cont et al. paper shows a roughly linear relationship
between OFI and short-horizon returns, with a slope that defines the *impact coefficient*.

**Static book imbalance.** A simpler feature: `(bid_size - ask_size) / (bid_size + ask_size)`
at the top, or aggregated over the top N levels. Easy, weakly predictive, and often a
useful baseline for ML features. Distinguish from OFI which is dynamic.

## Layer 3 — Toxic flow (Kyle's lambda, VPIN)

**Kyle's lambda** (Kyle 1985) is the price-impact coefficient in the regression of
returns on signed order flow: `return = λ × signed_volume + noise`. Higher lambda means
each unit of net buying pushes prices more, which means the market maker faces more
adverse selection. Lambda is the *cost-of-immediacy* benchmark.

**VPIN** (Volume-Synchronized Probability of Informed Trading; Easley, López de Prado,
O'Hara 2012) is a real-time estimator of order-flow toxicity. The recipe:

1. Bucket trades into equal-volume bars (e.g. 1/50 of average daily volume per bar).
2. For each volume bar, compute buy volume `V_B` and sell volume `V_S` (classified by
   tick rule or Lee-Ready).
3. VPIN over a window of N volume bars = `Σ |V_B - V_S| / (N × V_bar)`.

High VPIN means recent flow has been one-sided, which historically precedes adverse
market-maker performance and, in extreme cases (e.g. May 6 2010 Flash Crash), liquidity
withdrawal. As an alpha signal it is weak; as a regime indicator or execution-throttle
it can be useful.

## Layer 4 — Footprint reading

A footprint chart shows, for each price level within a bar, the buy volume vs sell
volume traded at that level. The patterns most discussed:

- **Imbalance row:** at one price level, buy volume is 3-5× sell volume (or vice versa).
  Often used as a discretionary signal; statistically weak in isolation.
- **Absorption:** large aggressive volume hits a level but price doesn't move — implies
  large hidden liquidity on the other side.
- **Exhaustion:** at the extreme of a move, aggressive volume tapers off and the opposite
  side starts to dominate — sometimes a reversal precursor.

Treat footprint patterns as candidate hypotheses, not signals. Each must be backtested
with proper labeling (see `feature-engineering`'s triple-barrier method) and survive the
multiple-testing budget from `ml-hypothesis-design`.

## Layer 5 — Queue position

When you place a passive limit order, your fill probability depends on *where in the queue*
you are. Queue position is not directly observable from L2 data — you only see total size
at each level. Estimation strategies:

- **Pessimistic estimate:** you are always at the back of the queue.
- **L3 (MBO) data:** if you have every individual order with an ID, queue position is exact.
  Databento and a few other vendors provide this.
- **Cancellation-aware estimate:** track size-at-level changes and assume FIFO with
  proportional cancellation.

Queue position dominates fill realism for passive strategies; backtests that ignore it
routinely overestimate fill rates by 2-5×.
