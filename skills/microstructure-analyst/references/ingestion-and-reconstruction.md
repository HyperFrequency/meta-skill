# Tape ingestion + L2/L3 reconstruction

Sections A and B of the microstructure-analyst toolkit. A covers raw tape
ingestion; B covers L2/L3 book reconstruction and validation.

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
the most common BVC implementation mistake — see Pitfall P3.

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
  `BacktestAsset().data(['path.npz'])` (see backtest-and-live.md D.3).
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
backtest-and-live.md D.2 for the full setup.
