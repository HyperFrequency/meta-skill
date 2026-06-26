---
name: microstructure-analyst
description: >
  Working market-microstructure analyst for tick + L2/L3 data. Use when the user
  mentions VPIN, OFI, "L2 orderbook", "tape data", "tick data backtest", "HFT",
  "order flow analysis", "OB imbalance", "micro-price", "Lee-Ready", "Bulk Volume
  Classification" / "BVC", "spoofing detection", "quote stuffing", "layering",
  "Kyle's lambda", "TPS spikes", "queue position", "footprint chart", "Hawkes",
  or "market microstructure indicators". Also trigger on phrases like "build a
  trade-sign classifier", "compute imbalance from these book deltas", "reconstruct
  the book from a snapshot+delta feed", "drive a Nautilus backtest from L2", or
  "is this dataset usable for an HFT backtest". Owns the pipeline from raw tape
  + L2 ingestion through indicator engine through backtest / live wiring. For
  pure conceptual framing of microstructure use `microstructure-analysis`; for
  cross-framework code ports use `strategy-translator`; for venue execution
  mechanics use `nautilus-trader`.
version: "1.0.0"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill, Agent
license: HyperFrequency original (citations to external academic + library work)
---

# Microstructure Analyst

This skill turns a Claude Code session into a working market-microstructure
analyst. Where the sibling `microstructure-analysis` skill is the *conceptual*
framework ("what is OFI, what does VPIN mean"), this one is the *operational*
toolkit: how to ingest 50 GB of compressed Tardis tape, reconstruct a Binance
L2 book from snapshot + delta, compute VPIN / OFI / micro-price / OB imbalance
correctly, detect spoofing live, and wire the resulting signals into a
NautilusTrader / vectorbt / hftbacktest backtest or a Hyperliquid live node.

Trigger on any of: VPIN, OFI, NVWAP, micro-price, Lee-Ready, BVC, L2/L3
order-book, tape data, spoofing/layering/quote-stuffing detection, TPS spikes,
queue position, Roll's spread, Kyle's lambda, Hawkes order flow, tick-data
backtest, HFT, hftbacktest. Read **When to use** first to decide whether
this skill or a sibling is the right entry point.

---

## When to use

- The user has tick or L2 data in hand (Tardis `.csv.gz`, Polygon flat files,
  Databento DBN, Nautilus `OrderBookDeltas` parquet, raw exchange JSON capture)
  and wants to do *something* with it — compute features, validate the book,
  resample to volume bars, train a model, run a backtest.
- The user asks for a specific microstructure indicator (VPIN, OFI, micro-price,
  Roll spread, queue-position estimate, OB imbalance, Hawkes intensity).
- The user is debugging a backtest whose fills don't match live, and the
  suspected cause is microstructure (queue position, latency, sweep timing).
- The user wants to detect spoofing / layering / quote-stuffing live and
  throttle execution when toxicity spikes.
- The user is building an HFT or market-making strategy and needs to choose
  between Nautilus, hftbacktest, or vectorbt as the backtest engine.
- The user asks how to drive `nautilus_trader.backtest.BacktestEngine` from L2
  deltas, or how to configure `LatencyModel` / `FillModel` realistically.

Do **not** use this skill for: daily-bar strategies (microstructure features
are noise at that horizon — use `vectorbt` directly); pure conceptual questions
about *why* a microstructure indicator works (route to `microstructure-analysis`);
or cross-framework strategy ports (route to `strategy-translator`).

---

## Required tooling — the unified gateway contract

Every documentation lookup, code-graph query, AST parse, and knowledge-graph
analysis routes through the **unified mcp2cli gateway** described in the
`neuro-harness` skill. Do not hand-roll API recommendations from training data.
The Nautilus / hftbacktest / Polars / DuckDB / Databento APIs change between
minor versions — a wrong import path that compiles silently and produces
plausible-looking numbers is the worst possible failure mode for a microstructure
pipeline.

| Task | Use | Why |
| --- | --- | --- |
| Confirm current API surface of `nautilus_trader.backtest.*`, `hftbacktest`, `tardis-machine`, `databento`, `polars`, `duckdb` | `docs-dual-lookup` skill (Context7 + Auggie in parallel) | Catches API drift between SDK versions. Auggie verifies against the actual `develop` branch; Context7 against curated upstream docs. |
| Parse a source strategy or research-paper code listing | `tree-sitter` skill via `mcp2cli tree-sitter parse|query` | Reliable AST nodes for function defs, calls, identifier locations. Required for Pine v5/v6. |
| Locate symbols / cross-references inside an existing strategy codebase | `mcp2cli gitnexus` or the `gitnexus-exploring` skill | Code-graph queries beat naive grep when an OFI implementation has 30 call sites. |
| Validate academic citations for indicators (Lee-Ready 1991, Kyle 1985, Cont-Kukanov-Stoikov 2014, Easley-LdP-O'Hara 2012/2016, Stoikov 2018, Bacry-Mastromatteo-Muzy 2015) | `paper-lookup` / `research-lookup` skills, then `WebFetch` of the canonical DOI | Every citation in this skill has been re-verified at last cross-check date. Do not introduce new ones without the same check. |
| LSP-style "what is this symbol" lookups on Nautilus / hftbacktest | The IDE LSP if available; otherwise tree-sitter via the gateway | True LSP is via the editor. Tree-sitter is the closest gateway proxy. |
| Knowledge-graph / topical-gap analysis on a microstructure paper corpus | `mcp2cli infranodus` or the `infranodus` skill (LOCAL OSS engine only) | Per `project_infranodus_local_only.md` — never default to infranodus.com. |

If `neuro-harness` is unreachable in the current environment (no compose stack,
sandboxed runtime), say so explicitly and degrade in this order: Context7
directly → WebFetch on the framework's docs site → training-data recall, flagged
with the source tier on each claim.

---

## Pipeline overview

```
Raw venue feed                Catalog                Indicator                 Strategy / Backtest / Live
─────────────────             ──────                 ─────────                 ──────────────────────────
Tardis .csv.gz   ─┐
Polygon flat     ─┼─► ingest ─► validate ─► store ─► VPIN / OFI / OB-imb ─► sample to bars ─► vectorbt
Databento DBN    ─┤   (Polars  (seq nums,  (parquet  micro-price, NVWAP,                       └─► ML
Binance WS JSON  ─┤   chunked   crossed    DuckDB,   TPS, Roll, Hawkes,
Hyperliquid WS   ─┤   reads,    book,      Nautilus  spoofing detector
NT parquet       ─┘   PDP)      gaps,      catalog)  └─► live throttle ─► Nautilus TradingNode
                                aggressor)                                  on Hyperliquid / Binance
```

The pipeline is **deliberately one-way and append-only** at the catalog layer.
If you find you need to mutate stored ticks, the bug is upstream — go fix the
ingest validator instead.

Section A covers raw tape ingestion. Section B covers L2/L3 reconstruction
and validation. Section C is the indicator catalog. Section D wires indicators
into a backtest. Section E wires them into a live node. Section F lists the
pre-built helpers in this repo so you can stop re-implementing things.

---

## Section A — Tape data processing

### A.1 Sources and what each one gives you

| Source | Trade tape | L1 quotes | L2 aggregated | L3 / MBO | Recommended reader |
| --- | --- | --- | --- | --- | --- |
| **Tardis** (`tardis-data-agent` skill) | yes — `trades` channel | yes — `book_change` top-of-book | yes — `book_snapshot_25` / `book_snapshot_5` + `book_change` deltas | partial (some venues) | `polars.scan_csv` over `.csv.gz`, then convert to parquet via the data-agent |
| **Polygon** (US equities) | yes — `trades` flat files | yes — `nbbo` / `quotes` flat files | no | no | `duckdb.read_csv_auto` with predicate pushdown on `participant_timestamp` |
| **Databento** | yes — `trades` (MBP-1 / TBBO) | yes | yes — `mbp-10` | yes — `mbo` (Market By Order, full L3) | `databento.DBNStore.from_file(path).to_df()` — schema-typed |
| **CCXT WebSocket** | yes (per-venue) | yes | partial (depends on subscription) | rare | direct streaming, persist to parquet via your own writer |
| **NautilusTrader parquet catalog** | yes — `TradeTick` | yes — `QuoteTick` | yes — `OrderBookDelta` (one row per atomic book event) | yes (if venue provides MBO) | `nautilus_trader.persistence.catalog.ParquetDataCatalog.from_uri(uri)` |

The Nautilus catalog has the cleanest schema for downstream work because it
forces every record into a canonical `(ts_event, ts_init, instrument_id, *)`
shape — see A.3 below for what those timestamp columns mean.

### A.2 Reading multi-GB compressed tape lazily (Polars / DuckDB)

Tardis ships `.csv.gz` files in the 1–10 GB compressed range per day per venue
per channel. Never load these into memory eagerly. Either:

```python
# Polars lazy: schema inference, predicate + projection pushdown, streaming exec.
import polars as pl

ldf = (
    pl.scan_csv(
        "tardis/binance-futures/trades/2026-04-15_BTCUSDT.csv.gz",
        # gzip is auto-detected from extension on Polars >= 0.20
        # Predicates and projections push down into the scan.
    )
    .filter(pl.col("symbol") == "BTCUSDT")
    .with_columns(
        # tardis-machine emits microseconds; cast once at the boundary
        pl.from_epoch("timestamp", time_unit="us").alias("ts"),
    )
    .select(["ts", "price", "amount", "side"])
)

# Stream through it without materialising the whole frame:
for chunk in ldf.collect(streaming=True).iter_slices(n_rows=1_000_000):
    process(chunk)
```

```python
# DuckDB: SQL with the same predicate/projection-pushdown discipline.
import duckdb

con = duckdb.connect()
df = con.execute("""
    SELECT
        epoch_us(timestamp) AS ts_us,
        price,
        amount,
        side
    FROM read_csv_auto(
        'tardis/binance-futures/trades/2026-04-15_BTCUSDT.csv.gz',
        compression = 'gzip'
    )
    WHERE symbol = 'BTCUSDT'
""").pl()  # pl() returns a Polars DataFrame; .arrow() for pyarrow
```

DuckDB's `read_csv_auto` handles gzip transparently and pushes the `WHERE`
into the scan — verified on DuckDB 0.10+ via Context7. Use DuckDB when you
want SQL ergonomics over multiple files (`read_csv_auto('tardis/**/*.csv.gz')`
with glob expansion); use Polars when you want to stay in DataFrame land.

### A.3 Wall-clock vs exchange vs `ts_event` vs `ts_init` (Nautilus convention)

This is the single biggest source of silent bugs in microstructure code.
There are at minimum **three** timestamps on every record:

1. **Exchange event time** — when the matching engine produced the event.
   In Nautilus, this is `ts_event` (nanoseconds since epoch, UTC).
2. **Capture / ingest time** — when our system first saw it. In Nautilus,
   `ts_init`. For live data this is the receive timestamp on our gateway;
   for replayed historical data it equals `ts_event`.
3. **Wall-clock / system time** — what `datetime.now()` says right now.
   Only meaningful in live mode.

Rules:

- All causal logic (signals, fills, look-back windows) must use `ts_event`.
  Using `ts_init` introduces a positive look-ahead bias proportional to
  network + parser latency.
- All latency measurement (e.g. "how stale is my book") uses `ts_init - ts_event`.
- Never mix `ts_event` from venue A with `ts_event` from venue B without a
  clock-skew estimate. Exchange clocks drift; the publicly published Binance
  vs Coinbase skew has been observed at 50–300 ms in past incidents.

Tardis-published timestamps are in *microseconds*, Nautilus stores
*nanoseconds*, Polygon and Databento publish *nanoseconds*. Cast once at the
ingest boundary; never `* 1000` mid-pipeline.

### A.4 Trade-sign classification

When the venue doesn't publish an aggressor-side flag, infer it. See the sibling
`microstructure-analysis` skill for the conceptual layered framework — this
skill provides the operational kernels.

#### Lee-Ready (with merge-asof)

For quote-based classification with a tunable reporting-lag, the canonical
Lee-Ready (1991) implementation in this stack is:

```python
import numpy as np
import pandas as pd

def lee_ready(trades: pd.DataFrame, quotes: pd.DataFrame,
              quote_lag_ms: int = 0) -> pd.Series:
    """Classify trades as buyer-initiated (+1) or seller-initiated (-1).

    trades: columns ['ts', 'price', 'size'], ts sorted ascending.
    quotes: columns ['ts', 'bid', 'ask'], ts sorted ascending.
    quote_lag_ms: Lee-Ready (1991) used 5000ms on 1990s NYSE data; modern
                  electronic markets often use 0. Validate against signed-trade
                  ground truth when available.

    Reference: Lee & Ready (1991), JoF 46(2), 733-746.
    """
    trades = trades.sort_values("ts").reset_index(drop=True)
    quotes = quotes.sort_values("ts").reset_index(drop=True)
    lookup = trades["ts"] - pd.Timedelta(milliseconds=quote_lag_ms)
    matched = pd.merge_asof(
        pd.DataFrame({"ts": lookup, "_i": trades.index}),
        quotes, on="ts", direction="backward",
    )
    mid = (matched["bid"] + matched["ask"]) / 2.0
    price = trades["price"].to_numpy()
    sign = np.where(price > mid, 1, np.where(price < mid, -1, 0))
    # Tick-rule fallback at midpoint
    diff = np.diff(price, prepend=price[0])
    tick = np.sign(diff)
    for i in range(1, len(tick)):
        if tick[i] == 0:
            tick[i] = tick[i - 1]
    sign = np.where(sign == 0, tick, sign)
    return pd.Series(sign, index=trades.index, name="sign")
```

#### Bulk Volume Classification (BVC)

When you only have OHLCV bars (no individual ticks), use BVC from Easley,
López de Prado, O'Hara (2016), "Discerning Information from Trade Data",
Journal of Financial Economics 120(2), 269–286:

```python
from scipy.stats import t as student_t

def bvc(bar_volume: pd.Series, bar_return: pd.Series,
        dof: float = 0.25) -> pd.DataFrame:
    """Bulk-Volume Classification — estimate buy/sell volume per bar from
    standardised returns and a Student-t CDF.

    bar_volume: per-bar total volume.
    bar_return: per-bar price change (close-to-close on bar grid).
    dof: degrees of freedom for the Student-t CDF (EdLdPO use ~0.25 in eq. (7)).

    Returns DataFrame with ['buy_vol', 'sell_vol'].
    Reference: Easley, López de Prado, O'Hara (2016), JFE 120(2).
    """
    sigma = bar_return.std()
    if sigma <= 0 or np.isnan(sigma):
        # No price variation in window — split 50/50 by convention.
        z = pd.Series(0.0, index=bar_return.index)
    else:
        z = bar_return / sigma
    buy_frac = student_t.cdf(z, df=dof)
    return pd.DataFrame({
        "buy_vol": bar_volume * buy_frac,
        "sell_vol": bar_volume * (1.0 - buy_frac),
    })
```

**Caveat:** BVC requires careful bar choice. The original paper uses *volume
bars*, not time bars, because volume-clocked returns are closer to Gaussian
than calendar-clocked returns. Using time bars and a naive Student-t df is
the most common BVC implementation mistake — see Pitfall P3 in the consolidated
list.

#### Aggressor-side flag (when the venue gives it)

Both Binance and Hyperliquid publish an `m` (or `is_buyer_maker`) flag on
public trades. When present, **use it** — it is ground truth from the matching
engine.

```python
# Binance USDT-M futures trade message shape:
# {'e': 'trade', 'p': '64512.30', 'q': '0.045', 'm': True, ...}
# 'm' == True  → buyer was the *maker* → trade was seller-initiated (-1)
# 'm' == False → seller was the maker → trade was buyer-initiated (+1)
def binance_aggressor_sign(is_buyer_maker: pd.Series) -> pd.Series:
    return pd.Series(np.where(is_buyer_maker, -1, 1),
                     index=is_buyer_maker.index, name="sign")
```

For Hyperliquid, the websocket `trades` payload includes `side` directly
(`"A"` for ask-side / sell aggressor, `"B"` for bid-side / buy aggressor on
the L1 perp feed) — verified against the Hyperliquid SDK as bundled in this
repo's `nautilus-trader` skill. If you ever see a venue-published aggressor
flag disagree with your Lee-Ready output by more than a percent or two of
trades, trust the flag and investigate the Lee-Ready inputs (clock skew,
lag setting, midpoint computation on stale quotes).

### A.5 Matched-trade pairs vs aggressor flag

Some venues publish *both* sides of every match as separate trade prints with
opposite `side` fields. Examples include certain CME ITCH feeds and some
options venues. Naively classifying these counts each match twice. The fix is
to deduplicate on `(timestamp, price, size, maker_order_id, taker_order_id)`
or, if order IDs are not present, on `(timestamp, price, size)` with a
microsecond tolerance window. Tardis already deduplicates for the venues it
covers; for raw exchange capture, check the venue's spec before trusting the
trade count.

---

## Section B — L2 / L3 reconstruction and validation

### B.1 Which level do you actually need

| Question | Minimum level |
| --- | --- |
| What is the bid-ask spread distribution? | L1 |
| What is OFI at the top of the book? | L1 (deltas) |
| What is the OB imbalance over the top 5 levels? | L2 |
| What is my queue position on a passive limit order? | L3 (MBO) |
| What is the size of hidden / iceberg liquidity? | L3 + trade-by-trade reconciliation |
| Are there spoofing / layering patterns? | L2 minimum; L3 strongly preferred |
| Hawkes intensity of trade arrivals? | trades only (L1 not needed) |

If you don't need L3, don't pay the storage cost — Databento L3 (`mbo`) is
roughly 10× larger than L2 (`mbp-10`) for the same symbol.

### B.2 Snapshot + delta reconstruction

The canonical exchange feed shape for L2 is:

1. On (re)connect, the venue sends an **initial snapshot** of the top N levels.
2. Thereafter, it sends **incremental updates** — one record per level change,
   with a `(price, new_size, side)` tuple plus a sequence number.

Pseudo-Python for the in-memory book:

```python
from sortedcontainers import SortedDict

class OrderBookL2:
    """Top-N L2 book with snapshot+delta semantics. Not thread-safe; one writer."""
    def __init__(self, depth: int = 25):
        self.depth = depth
        self.bids = SortedDict()   # price -> size, descending iteration via reversed()
        self.asks = SortedDict()   # price -> size, ascending iteration
        self.last_seq: int | None = None
        self.last_ts_event: int | None = None

    def apply_snapshot(self, bids: list, asks: list, seq: int, ts_event: int):
        self.bids.clear(); self.asks.clear()
        for p, s in bids: self.bids[p] = s
        for p, s in asks: self.asks[p] = s
        self.last_seq = seq
        self.last_ts_event = ts_event

    def apply_delta(self, price: float, new_size: float, side: str,
                    seq: int, ts_event: int) -> bool:
        """Returns True if applied cleanly, False on sequence gap (caller resyncs)."""
        if self.last_seq is not None and seq != self.last_seq + 1:
            return False  # gap — caller must request a fresh snapshot
        book = self.bids if side == "bid" else self.asks
        if new_size == 0:
            book.pop(price, None)
        else:
            book[price] = new_size
        self.last_seq = seq
        self.last_ts_event = ts_event
        return True

    def best_bid(self): return next(reversed(self.bids), None) if self.bids else None
    def best_ask(self): return next(iter(self.asks), None) if self.asks else None
```

`sortedcontainers.SortedDict` is acceptable for research-grade reconstruction;
for production HFT you want a flat numpy `(price, size)` array or a tree
structure in Rust (NautilusTrader's `OrderBook` is in Rust and exposes a
Python facade). For research, `SortedDict` is O(log N) for inserts and removes
which is fine at L2 depths ≤ 50.

### B.3 Book consistency validators (run on every record in CI)

1. **No crossed book.** `best_bid < best_ask` always. If violated, either you
   have a sequence gap, you reordered records, or the venue itself produced a
   pathological state during a market halt — log and quarantine.
2. **Sequence monotonicity.** Every delta increments `seq` by exactly 1 (or
   by `event_count` for venues that batch). Gap → resync.
3. **Snapshot reconciliation.** Periodically (every N deltas, or on a slow
   topic), the venue rebroadcasts a full snapshot. Compare every level —
   any mismatch means our incremental state is corrupt; resync.
4. **Sane price grid.** Bids ≤ best_bid; asks ≥ best_ask; prices are integer
   multiples of `tick_size`. The third check catches stray data-vendor
   floating-point errors that quietly survive.

A minimal validator over a stream of deltas:

```python
def validate_book(book: OrderBookL2) -> list[str]:
    errs = []
    bb, ba = book.best_bid(), book.best_ask()
    if bb is not None and ba is not None and bb >= ba:
        errs.append(f"crossed: bid={bb} ask={ba}")
    for p in book.bids:
        if bb is not None and p > bb:
            errs.append(f"bid above best: {p} > {bb}")
    for p in book.asks:
        if ba is not None and p < ba:
            errs.append(f"ask below best: {p} < {ba}")
    return errs
```

### B.4 Reconnect-and-replay protocol

On a sequence gap or a websocket disconnect:

1. Buffer incoming deltas (don't apply them).
2. Request a fresh snapshot (REST endpoint on most venues).
3. Discard buffered deltas with `seq <= snapshot_seq`.
4. Apply remaining buffered deltas in order.
5. Resume streaming.

If the buffer fills before the snapshot arrives, drop the oldest deltas and
log a data-quality event. Never silently skip the snapshot step — partial
recovery from a stale book is worse than a clean reset.

### B.5 Storage formats

- **Parquet** (columnar, predicate pushdown, ~5–10× compression on L2 deltas
  with `ZSTD`) — use for archival and for feeding `vectorbt` / pandas pipelines.
  Schema: `(ts_event, ts_init, instrument_id, action {ADD/UPDATE/DELETE},
  side, price, size, level_idx, seq)`.
- **Numpy `.npz` with a structured dtype** — what `hftbacktest` consumes
  natively. Verified via Context7: the canonical loader is
  `BacktestAsset().data(['path.npz'])` (see Section D.3).
- **NautilusTrader catalog** — wraps parquet with a typed schema enforced by
  `nautilus_trader.persistence.catalog.ParquetDataCatalog`. Use when the same
  data needs to drive both research and Nautilus backtests.

For numba-friendly in-memory work (when you're iterating an indicator over
500 M events on one machine), convert L2 deltas to a structured numpy array
with fixed-width fields (no Python objects) and write a `@numba.njit` kernel.
This is 50–200× faster than a pandas / Polars loop for tight per-event logic.

### B.6 NautilusTrader `OrderBookDeltas` integration

Nautilus represents incremental book updates as `OrderBookDeltas`, a wrapper
around a list of `OrderBookDelta` records. A strategy subscribes via
`self.subscribe_order_book_deltas(instrument_id, book_type=BookType.L2_MBP)` and
receives them in `on_order_book_deltas(self, deltas: OrderBookDeltas)`.
Verified against Nautilus develop docs via Context7: handlers `on_order_book`
and `on_order_book_deltas` are part of the `Strategy` base class.

If you already have a parquet of L2 deltas in another schema, write a small
adapter that emits `OrderBookDelta` records (one per row) and feed them into
a `BacktestEngine` via `engine.add_data(deltas, instrument_id)`. See
Section D.2 for the full setup.

---

## Section C — Microstructure indicators

For each indicator: a 1-paragraph intuition, the math, a working Python kernel
(≤ 30 lines, real imports), an interpretation guide, and 2–3 common pitfalls.
Where the math is more thoroughly motivated in the sibling
`microstructure-analysis` skill, this skill cross-links rather than duplicating.

### VPIN (Volume-Synchronized Probability of Informed Trading)

**Intuition.** VPIN is a real-time estimator of order-flow *toxicity*: how
one-sided recent flow has been. The key trick is to clock by *volume*, not
time, because under heavy informed trading the volume clock and the
information clock are approximately the same — equal-volume buckets give a
stable estimator regardless of whether the trader is fast or slow.

**Math.** Bucket trades into equal-volume bars of size `V` each. For each
bucket compute buy volume `V_B` and sell volume `V_S` (with `V_B + V_S = V`).
Over a rolling window of `n` buckets:

```
VPIN = (1 / (n × V)) × Σ_{i=1..n} |V_B_i - V_S_i|
```

VPIN is bounded in [0, 1]; persistent values > 0.4 are large in equities and
have historically preceded liquidity withdrawal events (Easley, López de Prado,
O'Hara 2012). The BVC variant replaces tick-rule classification of `V_B / V_S`
inside each volume bar with the BVC estimator from Section A.4.

**Implementation:**

```python
def vpin(trades: pd.DataFrame, volume_per_bucket: float,
         window_buckets: int = 50) -> pd.Series:
    """VPIN over rolling volume buckets.

    trades: ['ts', 'price', 'size', 'sign'] — sign from Lee-Ready or BVC.
    volume_per_bucket: target V per bucket, e.g. 1/50 of avg daily volume.
    window_buckets: n, default 50.

    Reference: Easley, López de Prado, O'Hara (2012), RFS 25(5), 1457-1493.
    """
    cum_vol = trades["size"].cumsum()
    bucket = (cum_vol // volume_per_bucket).astype(int)
    buy = (trades["size"] * (trades["sign"] == 1)).groupby(bucket).sum()
    sell = (trades["size"] * (trades["sign"] == -1)).groupby(bucket).sum()
    imbalance = (buy - sell).abs()
    return (imbalance.rolling(window_buckets).sum() /
            (window_buckets * volume_per_bucket)).rename("vpin")
```

**Interpretation.** Treat VPIN as a *regime* / *toxicity* indicator, not as
directional alpha. Use it to throttle execution (widen quotes, reduce size,
or step out) when persistently elevated; do not use it to predict the sign
of the next return.

**Pitfalls.**
- Time-bucketing instead of volume-bucketing. The "VPIN" you get from time
  buckets is a different, much weaker statistic.
- Look-ahead bias when the last partial bucket spills into the next: only
  emit VPIN for *complete* buckets.
- Mis-tuned `volume_per_bucket`. The canonical choice is ~1/50 of recent
  average daily volume; on illiquid instruments where ADV is unstable, use a
  rolling-trailing ADV rather than a fixed constant.

### NVWAP / VWAP family

**Intuition.** VWAP (Volume-Weighted Average Price) is the price you'd have
paid if you executed proportionally to total market volume. NVWAP normalises
VWAP into a comparable feature across instruments. TWAP ignores volume and
weights only by time — useful as a benchmark for execution-quality measurement,
not as an indicator.

**Math.** Over a window `W`:

```
VWAP   = Σ (price_i × size_i) / Σ size_i        # i ∈ W
TWAP   = (1/|W|) × Σ price_i
NVWAP  = (price - VWAP) / σ_price               # standardised deviation from VWAP
```

Anchored VWAP fixes the start of the window at a specific event (session open,
news print, swing high/low) and runs cumulatively from there.

**Implementation:**

```python
def vwap(prices: pd.Series, sizes: pd.Series,
         window: str = "1h") -> pd.Series:
    """Rolling time-window VWAP. Requires DatetimeIndex on `prices` and `sizes`.

    For anchored VWAP, pass `window=None` and use cumsum() instead of rolling.
    """
    pv = (prices * sizes).rolling(window).sum()
    v = sizes.rolling(window).sum()
    return (pv / v).rename("vwap")


def nvwap(prices: pd.Series, sizes: pd.Series,
          window: str = "1h", std_window: str = "1d") -> pd.Series:
    """Normalised VWAP deviation = (price - VWAP) / rolling stdev of price."""
    vw = vwap(prices, sizes, window)
    sigma = prices.rolling(std_window).std()
    return ((prices - vw) / sigma).rename("nvwap")
```

**Interpretation.** Positive NVWAP means price is trading above its
volume-weighted recent average — possible mean-reversion or trend-following
setup depending on the cross-sectional context. Anchored VWAP is heavily used
in discretionary day-trading as a level reference; treat any backtest of an
"anchored VWAP touch" strategy with extra skepticism around how the anchor
was chosen.

**Pitfalls.**
- Bar-VWAP vs tick-VWAP. Bar-aggregated VWAP loses sub-bar volume distribution
  information. For HFT signals, compute on ticks.
- Survivorship in anchor selection. Cherry-picking "the VWAP from the swing
  low" introduces look-ahead.

### Order-book imbalance (top-of-book, weighted, micro-price)

**Intuition.** When the bid is much bigger than the ask, marginal buyers will
have to walk the book further than marginal sellers — short-horizon price
drift biases up. The simplest version is the size ratio at the top of book.

**Math.**

```
I_top      = (bid_size - ask_size) / (bid_size + ask_size)         # ∈ [-1, +1]
I_weighted = Σ_k w_k (bid_size_k - ask_size_k) / Σ_k w_k (bid_size_k + ask_size_k)
             # with w_k a depth weight, e.g. 1 / (1 + |distance from mid|)
micro_price = (ask_size × bid + bid_size × ask) / (bid_size + ask_size)
             # Stoikov (2018) — sizes weight the *opposite* side's price
```

The Stoikov (2018) micro-price is *not* simply the size-weighted midpoint —
note the cross-weighting: the **ask** size weights the **bid** price, and
vice versa. Intuition: the side with more size is harder to lift, so the
fair price sits closer to the side with *less* size.

**Implementation:**

```python
def top_imbalance(bid_size, ask_size):
    return (bid_size - ask_size) / (bid_size + ask_size + 1e-12)

def weighted_imbalance(bid_sizes, ask_sizes, levels: int = 5,
                       decay: float = 0.5):
    """bid_sizes, ask_sizes: array-like of size at level 0..N-1.
    Decay weights deeper levels less."""
    w = np.exp(-decay * np.arange(levels))
    nb = np.dot(w, bid_sizes[:levels])
    na = np.dot(w, ask_sizes[:levels])
    return (nb - na) / (nb + na + 1e-12)

def stoikov_micro_price(bid, ask, bid_size, ask_size):
    """Stoikov (2018), Quantitative Finance 18(12), 1959-1966.
    Note the cross-weighting: ask SIZE * BID + bid SIZE * ASK."""
    denom = bid_size + ask_size
    return (ask_size * bid + bid_size * ask) / denom

def book_pressure(bid_sizes, ask_sizes, levels: int = 10):
    """Simple cumulative-depth imbalance over top N levels."""
    nb = np.sum(bid_sizes[:levels]); na = np.sum(ask_sizes[:levels])
    return (nb - na) / (nb + na + 1e-12)
```

**Interpretation.** `I_top` ∈ (+0.4, +1] is heavily bid-leaning; expect mean
reversion of recent down-moves and continuation of recent up-moves on the
seconds horizon. The micro-price is widely used as the *fair price reference*
for market-making quote placement — quote half-spread above and below it
rather than above and below the mid.

**Pitfalls.**
- Top-of-book only is brittle. A large `I_top` can flip on a single
  cancellation. Use `I_weighted` or `book_pressure` for stable signals.
- Don't conflate snapshot imbalance with OFI (flow). They have different
  signs in regimes like queue build-up (large positive `I_top`, low OFI).

### OFI — Order Flow Imbalance (Cont-Kukanov-Stoikov 2014)

**Intuition.** OFI measures the *net change* in liquidity at the top of the
book over a window — limit-order arrivals on the bid increase OFI, cancels on
the bid decrease it, and the ask side contributes with opposite sign. Unlike
static imbalance, OFI is event-flow-based, and the Cont-Kukanov-Stoikov (2014)
paper shows an approximately linear relationship between windowed OFI and
contemporaneous short-horizon returns.

**Math.** For each event with previous and current `(bid, bid_size, ask, ask_size)`:

```
e_n = +bid_size_n              if bid_n > bid_{n-1}
    = bid_size_n - bid_size_{n-1}   if bid_n = bid_{n-1}
    = -bid_size_{n-1}          if bid_n < bid_{n-1}

f_n = -ask_size_n              if ask_n > ask_{n-1}
    = ask_size_n - ask_size_{n-1}   if ask_n = ask_{n-1}
    = +ask_size_{n-1}          if ask_n < ask_{n-1}

OFI contribution_n = e_n + f_n
```

**Implementation:**

```python
def ofi(book_events: pd.DataFrame) -> pd.Series:
    """Per-event OFI contributions at top of book.

    book_events: ['ts', 'bid', 'bid_size', 'ask', 'ask_size'], one row per
    book update.  Sum over a window for the windowed OFI feature.

    Reference: Cont, Kukanov, Stoikov (2014), J. Financial Econometrics 12(1),
    47-88. arXiv:1011.6402.
    """
    b = book_events
    pb, pa = b["bid"].shift(1), b["ask"].shift(1)
    pbs, pas = b["bid_size"].shift(1), b["ask_size"].shift(1)
    e = np.where(b["bid"] > pb, b["bid_size"],
        np.where(b["bid"] == pb, b["bid_size"] - pbs, -pbs))
    f = np.where(b["ask"] > pa, -b["ask_size"],
        np.where(b["ask"] == pa, -(b["ask_size"] - pas), pas))
    return pd.Series(e + f, index=b.index, name="ofi").fillna(0.0)
```

**Interpretation.** Cont-Kukanov-Stoikov regress 10-second returns on summed
OFI over the same window and obtain `R² ≈ 0.65` for large-cap NYSE stocks.
The slope is the *impact coefficient* — useful as a per-instrument liquidity
parameter for execution-cost models.

**Pitfalls.**
- Sign error on the ask side. The CKS sign convention is that ask flow
  contributes with the *opposite* sign of bid flow because ask increases are
  bearish pressure, not bullish. Easy to flip by accident.
- Aggregating over wall-clock windows on event-time data. Sum OFI in
  *event-count* or *trade-volume* buckets if you want stable regressions.

### Spoofing / layering / quote-stuffing detection

**Intuition.** Spoofing is placing a large order with no intent to fill, to
move the price for a passive position on the opposite side. Layering is the
multi-level variant. Quote stuffing is a flood of cancel-replace at extreme
rates intended to slow competitors' market-data parsing or trigger their
adverse-selection signals. None of these patterns has a single canonical
academic detector — published work (Lee, Eom, Park 2013; Tao et al. 2020)
focuses on ex-post forensic detection on regulator-style L3 data with account
IDs. In the public-data setting, detection is **heuristic** — be honest about
that.

**Heuristics (paper-grounded):**

1. **Large-quote-then-cancel (LdP/Easley-style "submission/cancellation
   ratio"; Lee-Eom-Park 2013):** for each price level, track
   `cancel_size_t / posted_size_t` over a rolling 1-minute window. A level
   where >90% of recently posted size is cancelled within < 200 ms is a
   spoofing-pattern candidate.
2. **Layering signature (Lee-Eom-Park 2013):** ≥ 3 levels on the same side
   posted near-simultaneously and cancelled near-simultaneously (clustering of
   post-times and cancel-times within < 50 ms windows).
3. **Quote-stuffing TPS spike:** TPS (transactions per second, counting
   *messages* including cancels) > 99.9th-percentile of trailing 1-hour
   distribution, with cancel/post ratio > 0.95 in the same window.

**Implementation (operational, not exhaustive):**

```python
def cancel_post_ratio(book_events: pd.DataFrame, level_price: float,
                      window: str = "1min") -> pd.Series:
    """For one price level: rolling cancel-vs-post ratio.

    book_events: ['ts','price','size_delta','action'] with action in
    {'POST','CANCEL','EXECUTE'}.  size_delta is the signed quantity change.
    """
    at_level = book_events[book_events["price"] == level_price].set_index("ts")
    posts = (at_level["action"] == "POST").rolling(window).sum()
    cancels = (at_level["action"] == "CANCEL").rolling(window).sum()
    return (cancels / (posts + 1e-9)).rename("cancel_post_ratio")


def layering_candidates(book_events: pd.DataFrame, side: str,
                        min_levels: int = 3, cluster_ms: int = 50):
    """Find candidate layering episodes: ≥ min_levels POSTs on `side` within
    cluster_ms, followed by ≥ min_levels CANCELs on `side` within cluster_ms,
    with the cancel cluster preceding any aggressive trade on the OPPOSITE side.
    Returns DataFrame of (cluster_post_ts, cluster_cancel_ts, levels).
    """
    same = book_events[book_events["side"] == side].copy()
    same["bin"] = (same["ts"].astype("int64") // (cluster_ms * 1_000_000))
    posts = same[same["action"] == "POST"].groupby("bin").size()
    cancels = same[same["action"] == "CANCEL"].groupby("bin").size()
    cands = []
    for post_bin, n_post in posts[posts >= min_levels].items():
        # look for matching cancel cluster within ~10 bins (heuristic)
        for cancel_bin in range(post_bin + 1, post_bin + 11):
            if cancels.get(cancel_bin, 0) >= min_levels:
                cands.append({"post_bin": post_bin, "cancel_bin": cancel_bin,
                              "n_post": n_post, "n_cancel": cancels[cancel_bin]})
                break
    return pd.DataFrame(cands)
```

**Confidence levels for the patterns above:**

- *Large-quote-then-cancel ratio:* paper-grounded in Lee, Eom, Park (2013),
  J. Financial Markets 16, 227–252. **Medium confidence** — the paper uses
  the exact statistic on KRX data with known accounts. The exact thresholds
  (90% / 200 ms) are folklore practitioner heuristics.
- *Layering cluster:* paper-grounded in Lee, Eom, Park (2013); also discussed
  in Tao, Day, Ling, Drapeau (2020) "On Detecting Spoofing Strategies in High
  Frequency Trading" (arXiv:2009.14818). **Low–medium confidence** — public
  detectors must reconstruct order IDs heuristically because public L2 feeds
  don't carry them.
- *Quote-stuffing TPS spike:* folklore + regulator anecdote (CFTC reports
  post-Flash-Crash). **Low confidence** as a robust detector — high TPS also
  occurs in benign liquidity events (news prints, exchange resync).

**Pitfalls.**
- False positives during news events — TPS and cancel-post ratios both spike
  legitimately. Always combine with a news-event filter.
- L2 aggregation hides the per-order story; layering on a venue with hidden
  orders is undetectable from public feed alone.
- Treating spoofing detection as an alpha signal. It's a *throttle* / *risk*
  signal — when it fires, reduce passive size or step out of the market, not
  the other way around.

### Transactions-per-second (TPS) regime detection

**Intuition.** TPS — message rate per unit time — encodes the venue's
"temperature". Burst regimes are systematically different from steady-state:
during bursts, top-of-book has shorter expected lifetime, latency to the
exchange matters more, and adverse selection on resting orders is higher.

**Math.** EWMA-smoothed TPS with regime detection on quantile thresholds:

```python
def tps_regime(events: pd.DataFrame, halflife_sec: float = 5.0,
               q_burst: float = 0.99, q_quiet: float = 0.10,
               quantile_window: str = "1h") -> pd.DataFrame:
    """EWMA TPS plus quantile-band regime label.

    events: ['ts'] with one row per event (trade or book update).
    Returns DataFrame ['tps','regime'] with regime ∈ {'quiet','normal','burst'}.
    """
    s = events.set_index("ts").assign(one=1)["one"]
    # bucket to 1s for stable EWMA; halflife in seconds
    per_sec = s.resample("1s").sum()
    tps = per_sec.ewm(halflife=halflife_sec, times=per_sec.index,
                      adjust=False).mean()
    burst = tps.rolling(quantile_window).quantile(q_burst)
    quiet = tps.rolling(quantile_window).quantile(q_quiet)
    regime = pd.Series("normal", index=tps.index)
    regime[tps >= burst] = "burst"
    regime[tps <= quiet] = "quiet"
    return pd.DataFrame({"tps": tps, "regime": regime})
```

**Interpretation.** In burst regimes, widen passive quotes (or step out), and
treat any signal that depends on book-state stability with more skepticism.
The correlation between TPS spikes and same-window absolute returns is the
basic input to a "volatility-of-flow" regime indicator.

**Pitfalls.**
- Aggregating across instruments dilutes the signal. Compute per-instrument.
- Mixing trade-TPS and quote-TPS without separating. Quote-TPS during quiet
  trading is normal market-maker churn; trade-TPS bursts are different.

### Order-book spread dynamics

**Intuition.** The spread is the round-trip cost of immediacy. Its
distribution, decay after a sweep, and dependence on volatility are core
inputs to any execution model and to market-making profitability calculations.

**Definitions.**

```
quoted_spread     = ask - bid
half_spread       = (ask - bid) / 2
effective_spread  = 2 × sign × (trade_price - mid_at_trade)    # per trade
realized_spread   = 2 × sign × (trade_price - mid_at_trade_plus_5min)
                                                                # decay window
roll_spread       = 2 × sqrt(-Cov(Δp_t, Δp_{t-1}))           # Roll (1984)
                                                                # quote-free estimator
```

`effective_spread` measures what the aggressor *actually paid*; the difference
to `quoted_spread` is the contribution of price improvement. `realized_spread`
measures what the *liquidity provider earned*, net of adverse selection, over
a decay window (Hasbrouck and Schwartz often use 5 minutes; for crypto HFT
30 seconds is more realistic). Roll's (1984) spread estimator backs out an
implied spread from autocovariance of price changes — useful when you only
have trades, no quotes.

**Implementation:**

```python
def effective_spread(trade_price, sign, mid_at_trade):
    return 2 * sign * (trade_price - mid_at_trade)

def realized_spread(trade_price, sign, mid_future, mid_at_trade):
    """mid_future = mid 5 minutes (or 30s for HFT) AFTER the trade."""
    return 2 * sign * (trade_price - mid_future)

def roll_spread(price_changes: pd.Series) -> float:
    """Roll (1984), Journal of Finance 39(4), 1127-1139.
    Returns implied spread from negative serial covariance of returns."""
    cov = price_changes.diff().cov(price_changes.diff().shift(1))
    return float(2.0 * np.sqrt(-cov)) if cov < 0 else float("nan")
```

**Pitfalls.**
- Mismatched `mid_at_trade`: must be the mid *just before* the trade prints,
  not the mid that includes the trade's impact. Use `merge_asof` with
  `direction='backward'` and a tolerance of microseconds.
- Roll's estimator returns NaN when the autocovariance is positive; that's
  a feature, not a bug — it tells you the data has trend autocorrelation that
  violates Roll's assumptions, and you shouldn't quote a spread from it.

### Order flow dynamics — Hawkes intensity

**Intuition.** Trade arrivals cluster — a buy market-order makes another buy
market-order more likely in the next 100 ms, because both are responses to
the same information shock. A Hawkes process is a self-exciting point process
that captures this: every event raises the conditional arrival intensity by
a kernel-weighted amount that decays over time.

**Math.** Univariate self-exciting Hawkes process with exponential kernel:

```
λ(t) = μ + Σ_{t_i < t} α × exp(-β × (t - t_i))
```

`μ` is baseline intensity, `α` is the self-excitation, `β` the decay rate.
Stability requires `α/β < 1`. The bivariate case (separate buy and sell
intensities with cross-excitation between them) is the standard Bacry-
Mastromatteo-Muzy (2015) setting.

**Implementation (using the `tick` library):**

```python
# pip install tick   (Bacry-Iutzeler-Mastromatteo-Bompaire 2017)
from tick.hawkes import HawkesExpKern

def fit_hawkes_buy_sell(buy_times: np.ndarray, sell_times: np.ndarray,
                       decay: float = 5.0):
    """Fit a 2-dim Hawkes process with one decay constant.

    buy_times, sell_times: 1-D arrays of event timestamps in seconds.
    decay: β in 1/seconds. Tune on a small grid by likelihood.

    Reference: Bacry, Mastromatteo, Muzy (2015), Market Microstructure and
    Liquidity 1(01), 1550005. arXiv:1502.04592.
    """
    learner = HawkesExpKern(decays=decay)
    learner.fit([[buy_times, sell_times]])
    return {
        "baseline": learner.baseline,         # shape (2,)
        "adjacency": learner.adjacency,       # shape (2, 2) — self + cross
        "score": learner.score(),
    }
```

**Interpretation.** The adjacency matrix's diagonal entries are the
self-excitation of buys-by-buys and sells-by-sells; off-diagonals are
cross-excitation. A diagonal entry near 1.0 means strong clustering (your
arrival-rate model needs Hawkes, not Poisson); cross-excitation tells you
whether buys and sells are reactive to each other or independent regimes.

**Pitfalls.**
- Decay parameter `β` is critical and not estimated jointly in `HawkesExpKern`
  (it's a fixed argument). Tune on a small grid; mis-specified decay
  silently biases the adjacency.
- Hawkes likelihood is non-convex; refit with different initialisations on
  long histories.
- Sub-millisecond timestamp granularity matters. Microsecond timestamps cast
  to floats lose precision over hours of trading — use seconds-since-anchor.

---

## Section D — Backtest setup using microstructure data

### D.1 vectorbt: sample ticks to volume bars first

`vectorbt` and `vectorbt-pro` are vectorized backtesters that consume
*regular* DataFrames. They are excellent for parameter sweeps and signal-based
strategies, but they do not natively consume tick-by-tick L2 events. The
canonical pattern: resample ticks to volume / dollar / tick bars, attach
microstructure features as additional columns, then drive `Portfolio.from_signals`.

```python
import vectorbt as vbt

def volume_bars(trades: pd.DataFrame, vol_per_bar: float) -> pd.DataFrame:
    """Resample to equal-volume bars. Returns ['open','high','low','close','volume']."""
    trades = trades.copy()
    trades["cum"] = trades["size"].cumsum()
    trades["bar"] = (trades["cum"] // vol_per_bar).astype(int)
    g = trades.groupby("bar")
    return pd.DataFrame({
        "open":  g["price"].first(),
        "high":  g["price"].max(),
        "low":   g["price"].min(),
        "close": g["price"].last(),
        "volume": g["size"].sum(),
        "ts":    g["ts"].last(),
    }).set_index("ts")
```

Volume bars are recommended over time bars for HFT signals because returns on
volume bars are closer to IID-Gaussian (the volume clock is closer to the
information clock). Dollar bars (constant notional per bar) are similar in
spirit and handle illiquid sessions better.

Once the bars are constructed, follow the standard `vectorbt` recipe; refer
to the `vectorbt` skill in this repo for parameter sweeps, walk-forward, and
tearsheet generation.

### D.2 NautilusTrader: drive `BacktestEngine` from L2 deltas

For event-driven backtests that respect book microstructure, Nautilus is the
right tool. The minimum pipeline:

```python
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.backtest.models import FillModel, LatencyModel
from nautilus_trader.config import LatencyModelConfig
from nautilus_trader.model.enums import OmsType, AccountType, BookType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money

engine = BacktestEngine(config=BacktestEngineConfig(trader_id="MS-001"))

# Realistic latency: 1ms base + 50us per-message order insert latency.
# Field names verified via Context7 against nautilus_trader develop docs.
latency = LatencyModel(
    base_latency_nanos=1_000_000,
    insert_latency_nanos=50_000,
    update_latency_nanos=50_000,
    cancel_latency_nanos=50_000,
)

# FillModel: tunable probabilistic adverse-selection.
fill = FillModel(
    prob_fill_on_limit=0.20,   # chance a limit order fills when price touches it
    prob_slippage=0.50,        # chance of 1-tick slippage (L1 mode only)
    random_seed=42,
)

engine.add_venue(
    venue=Venue("BINANCE"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    starting_balances=[Money(100_000, "USDT")],
    book_type=BookType.L2_MBP,    # match the data we're feeding in
    latency_model=latency,
    fill_model=fill,
)

# Load instrument + L2 deltas from the parquet catalog.
# catalog = ParquetDataCatalog.from_uri("./catalog")
# deltas = catalog.order_book_deltas(instrument_ids=["BTCUSDT.BINANCE"])
# engine.add_data(deltas, client_id=...)
# engine.add_strategy(MyMicrostructureStrategy(...))
# engine.run()
```

`BookType.L2_MBP` is "L2 market-by-price"; switch to `BookType.L3_MBO` if you
have full market-by-order data and want queue-position-aware fills. The
`OrderBookDeltas` you feed in must match the declared book type — mixing
will be silently lossy.

For the full Nautilus engine wiring (data catalog, instruments, multi-venue
routing), defer to the `nautilus-trader` skill in this repo. This skill owns
the microstructure-feature side; that skill owns execution mechanics.

### D.3 hftbacktest: when you need book-level queue-position fidelity

`hftbacktest` (a HyperFrequency fork at `HyperFrequency/hftbacktest`,
upstream `nkaz001/hftbacktest`) is purpose-built for market-making and
HFT backtests where queue position and per-message latency are first-class
concerns. Use it over Nautilus when:

- You're optimising market-making spread/skew parameters and need accurate
  fill-rate-per-queue-position.
- You need per-message order-entry-and-response latency modelling (Nautilus's
  `LatencyModel` is a single set of constants; `hftbacktest` supports
  measured-latency replay from `.npz`).
- Your strategy depends on tick-by-tick book state visible to a maker
  (the "what is my expected queue position right now" question).

Minimum setup (verified via Context7 against the canonical examples on
the `hftbacktest` repo):

```python
from hftbacktest import BacktestAsset, ROIVectorMarketDepthBacktest

asset = (
    BacktestAsset()
        .data(["data/btcusdt_20260415.npz"])         # tick + book deltas
        .initial_snapshot("data/btcusdt_eod.npz")    # opening book state
        .linear_asset(1.0)                            # USDT-margined linear
        .constant_order_latency(500_000, 500_000)    # 500us / 500us in nanoseconds
        # or .intp_order_latency(["latency/2026-04-15.npz"]) for measured replay
        .power_prob_queue_model(3)                    # probabilistic queue model
        .no_partial_fill_exchange()                   # all-or-nothing fills
        .trading_value_fee_model(-0.00005, 0.0007)   # maker rebate, taker fee
        .tick_size(0.1)
        .lot_size(0.001)
)
hbt = ROIVectorMarketDepthBacktest([asset])
# strategy = your numba-jit'd market-making function
# strategy(hbt, recorder.recorder, ...)
# hbt.close()
```

The `power_prob_queue_model(3)` gives a probabilistic fill model that
respects queue position — the canonical alternative to `RiskAdverseQueueModel`
(always at back) and `IdentityProbQueueModel` (fill iff fully consumed).

### D.4 Latency model selection

| Need | Use | Notes |
| --- | --- | --- |
| Quick research on bar-level signals | None (`LatencyModel(0, 0, 0, 0)`) | Latency is rounding error at bar scale. |
| Realistic per-trade slippage on a daily strategy | Nautilus default (`1ms base`) | The 1ms default is documented; see LatencyModelConfig in Section D.2. |
| HFT / market-making | `hftbacktest` with `intp_order_latency()` driven by **measured** round-trip latency | The constant-latency model is a strong floor for HFT realism but biases toward optimism. |
| Co-located HFT in production | Measured per-message latency replay with jitter distribution | If you don't have measured latencies for the venue + region, your backtest is a fiction at this end of the latency curve. |

### D.5 Fill model selection

- **Aggressive (taker) orders:** at the venue match price, with slippage equal
  to the realized walk-through cost over the L2 book. Both Nautilus
  (`BookType.L2_MBP` with the matching engine) and `hftbacktest` model this
  correctly out of the box.
- **Passive (maker) orders:** at the resting price, *iff* you survive to the
  front of the queue. Nautilus's `FillModel(prob_fill_on_limit=...)` is a
  blunt probabilistic abstraction; `hftbacktest`'s `power_prob_queue_model`
  is queue-position-aware and is the correct choice for any HFT/MM backtest.
- **Iceberg / hidden liquidity:** neither tool surfaces hidden orders by
  default. If you have trade-by-trade reconciliation that shows fills against
  invisible depth, model the effective depth-augmented book as a custom data
  source.

---

## Section E — Live trading hookup

### E.1 Wiring tape + L2 into an in-memory book and indicator engine

The live path mirrors the backtest:

```
WS feed → parser → OrderBookL2 (Section B.2) → IndicatorEngine ─┬─► Strategy ─► OrderRouter
                                          │                     └─► Risk / throttle
                                          └─► snapshot writer ─► parquet (for replay)
```

For NautilusTrader, this is what `TradingNode` does end-to-end: it wires the
venue adapter (Binance, Hyperliquid, Coinbase, etc.) into the message bus,
exposes `OrderBookDeltas` to your `Strategy`, and routes orders out the
configured adapter. See the `nautilus-trader` skill's
`references/live_trading.py` for the canonical Hyperliquid mainnet wiring
in this repo (including the Hyperliquid SDK patch documented in that skill).

For a hand-rolled live loop without Nautilus (e.g. when you want one process
to handle a custom venue), the rough shape is:

```python
import asyncio
import websockets

class LiveBookRunner:
    def __init__(self, book: OrderBookL2, indicator_engine, strategy):
        self.book = book; self.ind = indicator_engine; self.strat = strategy
        self.last_seq: int | None = None

    async def consume(self, ws):
        async for raw in ws:
            msg = parse(raw)  # venue-specific parser → snapshot or delta
            if msg.kind == "snapshot":
                self.book.apply_snapshot(msg.bids, msg.asks, msg.seq, msg.ts_event)
                self.last_seq = msg.seq
            else:
                ok = self.book.apply_delta(msg.price, msg.new_size, msg.side,
                                            msg.seq, msg.ts_event)
                if not ok:
                    await self.resync(ws)
                    continue
            features = self.ind.update(self.book, msg.ts_event)
            self.strat.on_features(features)
```

Don't try to recreate Nautilus's `TradingNode` ergonomics from scratch unless
you have a reason. The hand-rolled version is mostly useful for *replaying*
captured live data against your strategy for debugging.

### E.2 Live throttle on spoofing / TPS-spike signals

The killer use case for microstructure indicators in live trading is the
**throttle**. The pattern:

```python
class MicrostructureThrottle:
    """Disable new passive orders when toxicity indicators spike.
    Returns one of {'normal', 'reduce', 'flat'}."""
    def __init__(self, vpin_warn=0.4, vpin_flat=0.55,
                 tps_burst_q=0.99, ofi_flip_ms=100):
        self.vpin_warn, self.vpin_flat = vpin_warn, vpin_flat
        self.tps_burst_q, self.ofi_flip_ms = tps_burst_q, ofi_flip_ms
        self._last_ofi_sign = 0
        self._ofi_flip_count = 0
        self._ofi_window_start = None

    def update(self, vpin: float, tps_quantile: float, ofi: float,
               now_ns: int) -> str:
        # OFI flip-counting in a 100ms window
        sign = int(np.sign(ofi))
        if self._ofi_window_start is None or now_ns - self._ofi_window_start > \
                self.ofi_flip_ms * 1_000_000:
            self._ofi_window_start = now_ns
            self._ofi_flip_count = 0
        if sign != 0 and sign != self._last_ofi_sign and self._last_ofi_sign != 0:
            self._ofi_flip_count += 1
        if sign != 0:
            self._last_ofi_sign = sign

        if vpin >= self.vpin_flat:
            return "flat"
        if vpin >= self.vpin_warn or tps_quantile >= self.tps_burst_q or \
           self._ofi_flip_count >= 4:
            return "reduce"
        return "normal"
```

`"flat"` means: cancel all passive orders and step out of the market.
`"reduce"` means: cancel the outermost layers and widen the active spread.
The exact thresholds (`vpin_flat=0.55`, OFI 4 flips in 100ms) are folklore
practitioner defaults — start there, then tune on shadow-mode logs of your
own venue. Treat the levels as L4 (priors) until your own logs say otherwise.

### E.3 Latency monitoring

Instrument the round-trip latency of every order from your strategy's emit
to the venue's `ts_event` of the fill:

```python
# Per-order latency dictionary keyed by client_order_id
self._sent_ns: dict[str, int] = {}

def on_order_sent(self, client_order_id, ts_now_ns):
    self._sent_ns[client_order_id] = ts_now_ns

def on_order_filled(self, client_order_id, ts_event_ns):
    sent = self._sent_ns.pop(client_order_id, None)
    if sent is not None:
        latency_us = (ts_event_ns - sent) / 1000
        prometheus_latency_histogram.observe(latency_us)
```

Aggregate to a Prometheus histogram and visualise the p50 / p99 / p99.9 over
time in Grafana. A widening p99.9 tail is your earliest warning sign of
venue congestion, network degradation, or local CPU contention. For the deploy
pattern (Prometheus + Grafana on the harness), see the `monorepo-deploy` and
`gitnexus-cli` skills in this repo.

---

## Section F — Pre-built helpers in the repo + ecosystem

### F.1 In-repo skills (already wired)

| Skill | What it owns | Cross-link to |
| --- | --- | --- |
| `nautilus-trader` | Venue wiring (Binance, Hyperliquid, etc.); `BacktestEngine`; `TradingNode`; Hyperliquid SDK patch. The execution-mechanics owner. | Section D.2, E.1 |
| `tardis-data-agent` | Tardis ingestion, manifest tracking, daily front-fill, CSV → parquet conversion, validation. The historical-data owner. | Section A.1, A.2 |
| `tearsheet-generator` | Performance + risk reporting on backtest outputs. The output owner. | Final stage of any backtest in Section D |
| `vectorbt` | Vectorised signal-based backtests, parameter sweeps, walk-forward. The bar-level backtest owner. | Section D.1 |
| `microstructure-analysis` | The *conceptual* framework — layered model, Lee-Ready / OFI / VPIN intuition. Sibling and dependency. | Throughout |
| `microstructure-feature-engineering` (sibling, when present) | Leakage-safe feature extraction on top of these indicators; triple-barrier labelling for tick-rate signals. | Use when handing features to ML |
| `strategy-translator` | Cross-framework strategy ports (vectorbt ↔ Nautilus ↔ Pine ↔ Rust). | Use when porting a microstructure strategy |
| `feature-engineering` | Generic ML feature workflows; triple-barrier; purged CV. | Use upstream of any ML on these features |
| `model-evaluation` | Purged + embargoed CV for HF financial ML. | Required for tick-rate model evaluation |

### F.2 External libraries (with caveats)

- **`mlfinlab`** — López de Prado's canonical reference implementation of
  BVC, fracdiff, triple-barrier, volume bars, Kyle's lambda. `pip install
  mlfinlab`. The license is restrictive (research only); read it before
  shipping production code that imports it.
- **`hftbacktest`** (HyperFrequency fork at `HyperFrequency/hftbacktest`,
  upstream `nkaz001/hftbacktest`) — book-level HFT backtester. See Section D.3.
- **`tick`** (Bacry et al.) — Hawkes processes, point-process fitting,
  multivariate kernels. `pip install tick`. Section C / Hawkes intensity.
- **`databento`** — Python SDK for Databento DBN data. Schema-typed
  L1 / L2 / L3 access; the cleanest commercial dataset for US equities and
  futures microstructure work.
- **`polars`** — lazy DataFrame, predicate pushdown. Section A.2.
- **`duckdb`** — SQL over parquet / CSV / arrow, predicate pushdown,
  glob expansion. Section A.2.
- **`sortedcontainers`** — Python sorted-dict / sorted-set for L2 book
  reconstruction in research-grade code. Section B.2.

### F.3 What this skill deliberately doesn't cover

- ML model architectures (LSTMs, transformers, GBTs) on microstructure features.
  Route to the `lstm-forecast`, `lightgbm`, `catboost`, `cnn-pattern-recognition`,
  `autoencoder-anomaly-detection` skills.
- Walk-forward optimisation and triple-barrier labelling. Route to
  `adaptive-wfo-epoch` and `feature-engineering`.
- Multi-venue arbitrage execution. Route to `nautilus-trader` for the
  routing layer.
- Pine Script ports of microstructure ideas. Route to `strategy-translator`.

---

## Consolidated common pitfalls

Numbered for cross-reference from the sections above.

**P1. Sequence-gap silent recovery.** A websocket reconnect that re-fires
old deltas without a snapshot leaves your book inconsistent. *Always* go
snapshot → buffered-deltas → resume. Never trust "we're back online" alone.

**P2. Tape vs book clock skew.** Trade prints and book updates can come from
different streams with different latencies. A naive merge-asof against the
book *as of the trade's ts_event* can attach a quote that the system hadn't
yet seen at trade time. Use `ts_init` for "what we knew at decision time" and
`ts_event` for causality, and document which one you used.

**P3. Look-ahead bias in BVC volume buckets.** BVC requires *complete* volume
buckets. If you label the in-progress bucket using its eventual close-price
return, you've leaked the bucket's own return into the classifier. Only
emit BVC for closed buckets, lagging the label by one bucket.

**P4. Sub-tick price reconstruction errors.** If a venue quotes in 0.1 ticks
and you parse JSON via `float`, you get drift like `64512.299999...`. Use
`Decimal` at the parser boundary and round to the venue's `tick_size` grid
before storing. NautilusTrader handles this in Rust; ad-hoc Python parsers
do not.

**P5. Static imbalance ≠ OFI.** They have different signs in queue-build-up
vs sweep regimes. A backtest that uses `I_top` where `OFI` was intended (or
vice versa) can have the right *direction* in 70% of regimes and the wrong
direction in 30%, which is hard to debug from PnL alone.

**P6. Treating spoofing detectors as alpha.** They're throttles, not directional
signals. If you sell when spoofing fires, you're acting *with* the spoofer.
Use the signal to widen quotes or step out, never to take.

**P7. FIFO assumption on a pro-rata venue.** Some CME options venues, the
Eurex options book, and certain CME futures use pro-rata or hybrid matching.
A FIFO queue-position estimate on a pro-rata venue is wrong in a way that
mostly *helps* the backtest — passive fills appear easier than reality.
Read the venue spec.

**P8. Hidden orders / iceberg fills.** L2 size shows only displayed depth.
Reconcile trade volume against displayed depth consumed; a persistent positive
residual is hidden liquidity that your indicators are blind to.

**P9. Aggregating event-time OFI on wall-clock windows.** Bins of "1 second
of wall-clock" contain wildly different numbers of events in burst vs quiet
regimes. Aggregate OFI in event-count or trade-volume bins for stable
regressions; use wall-clock only as a downstream feature.

**P10. Hawkes decay parameter assumed not estimated.** `HawkesExpKern`'s
`decays` argument is fixed at fit time. Mis-specified decay silently biases
the adjacency matrix. Sweep over `decay ∈ {1, 2, 5, 10, 30}` seconds and
take the best-likelihood fit.

---

## References

**Primary library / Deep-dive docs (verified via Context7 last cross-check
date, see bottom of file).**

- NautilusTrader documentation, `docs.nautilustrader.io` and the in-repo
  `nautilus_trader/docs/api_reference/backtest.md`. `BacktestEngine`,
  `LatencyModel` / `LatencyModelConfig`, `FillModel`, `OrderBookDeltas`,
  `BookType`, `OrderBookL1_MBP`/`L2_MBP`/`L3_MBO`. Verified via Context7
  `/nautechsystems/nautilus_trader`.
- `hftbacktest` documentation, `https://hftbacktest.readthedocs.io/`.
  `BacktestAsset`, `ROIVectorMarketDepthBacktest`, `power_prob_queue_model`,
  `intp_order_latency`, `trading_value_fee_model`. Verified via Context7
  `/nkaz001/hftbacktest`.
- Polars user guide, `https://docs.pola.rs/`. `scan_csv`, lazy / streaming
  execution, `iter_slices`.
- DuckDB documentation, `https://duckdb.org/docs/`. `read_csv_auto`, parquet
  scans, predicate pushdown.
- `tick` library, `https://x-datainitiative.github.io/tick/`. `HawkesExpKern`,
  multivariate point processes.
- `databento-python`, `https://databento.com/docs/`. `DBNStore`, schemas
  (`mbp-1`, `mbp-10`, `mbo`).

**Adjacent libraries.**

- `mlfinlab` (`https://github.com/hudson-and-thames/mlfinlab`) — canonical
  Lopez de Prado reference. BVC, fractional differentiation, triple-barrier,
  Kyle's lambda. Research-license only.
- `vectorbt` / `vectorbt-pro` — see the in-repo `vectorbt` skill for the
  full surface.

**Academic papers (each verified to exist at last cross-check).**

- Lee, C. M. C., & Ready, M. J. (1991). Inferring Trade Direction from Intraday
  Data. *Journal of Finance*, 46(2), 733–746.
  DOI: 10.1111/j.1540-6261.1991.tb02683.x. Verified.
- Kyle, A. S. (1985). Continuous Auctions and Insider Trading. *Econometrica*,
  53(6), 1315–1335. Verified.
- Roll, R. (1984). A Simple Implicit Measure of the Effective Bid-Ask Spread
  in an Efficient Market. *Journal of Finance*, 39(4), 1127–1139.
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The Price Impact of Order
  Book Events. *Journal of Financial Econometrics*, 12(1), 47–88.
  DOI: 10.1093/jjfinec/nbt003. arXiv:1011.6402.
  Verified via WebFetch of `arxiv.org/abs/1011.6402` (title, authors,
  venue match).
- Easley, D., López de Prado, M. M., & O'Hara, M. (2012). Flow Toxicity and
  Liquidity in a High-Frequency World. *Review of Financial Studies*, 25(5),
  1457–1493. SSRN: 1695596. Verified by metadata via WebSearch
  (SSRN direct fetch returned HTTP 403; this is a captcha block, not a
  missing paper).
- Easley, D., López de Prado, M. M., & O'Hara, M. (2016). Discerning
  Information from Trade Data. *Journal of Financial Economics*, 120(2),
  269–286. SSRN: 1989555. Verified via WebSearch.
- Stoikov, S. (2018). The micro-price: a high-frequency estimator of future
  prices. *Quantitative Finance*, 18(12), 1959–1966.
  DOI: 10.1080/14697688.2018.1489139. SSRN: 2970694. Verified via WebSearch.
- Bacry, E., Mastromatteo, I., & Muzy, J.-F. (2015). Hawkes Processes in
  Finance. *Market Microstructure and Liquidity*, 1(01), 1550005.
  arXiv:1502.04592. Verified via WebSearch (title, authors, journal match).
- Lee, E. J., Eom, K. S., & Park, K. S. (2013). Microstructure-Based
  Manipulation: Strategic Behavior and Performance of Spoofing Traders.
  *Journal of Financial Markets*, 16, 227–252.
  SSRN: 1328899. Verified via WebSearch.
- Tao, X., Day, A., Ling, L., & Drapeau, S. (2020). On Detecting Spoofing
  Strategies in High Frequency Trading. arXiv:2009.14818. Verified via
  WebSearch.
- Hasbrouck, J. (2007). *Empirical Market Microstructure*. Oxford University
  Press. ISBN 9780195301649.
- O'Hara, M. (1995). *Market Microstructure Theory*. Blackwell.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
  Chapter 19 covers microstructure features in production.

**Tutorials and explanatory notes (use with skepticism — none have the
authority of the journal-published papers above).**

- Stoikov micro-price intuition note: `https://arxiv.org/pdf/2307.15599`
  ("Understanding the worst-kept secret of high-frequency trading") —
  Pulido's commentary on the micro-price; provides a clean derivation.

**Standard datasets.**

- Tardis (`tardis.dev`) — crypto venues, L2 / L3 / trades / funding /
  liquidations. Wired in this repo via the `tardis-data-agent` skill.
- Databento — US equities, futures, options. Best-in-class L3 / MBO for
  US listed markets.
- Polygon.io — US equities and options flat files. Cheaper than Databento;
  fewer schema niceties.
- CME DataMine — futures and options on futures, MBO available.

**Last cross-checked:** 2026-05-20. NautilusTrader API confirmed against
`develop`-branch docs via Context7. `hftbacktest` API confirmed via Context7
against the `nkaz001/hftbacktest` examples notebooks. All academic citations
re-verified against arXiv / journal metadata via WebSearch + WebFetch.
