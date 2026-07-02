# Backtest setup + live trading hookup

Sections D and E of the toolkit. D wires microstructure features into a
backtest engine; E wires them into a live node.

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
| Realistic per-trade slippage on a daily strategy | Nautilus default (`1ms base`) | The 1ms default is documented; see LatencyModelConfig in D.2. |
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
WS feed → parser → OrderBookL2 (recon B.2) → IndicatorEngine ─┬─► Strategy ─► OrderRouter
                                          │                   └─► Risk / throttle
                                          └─► snapshot writer ─► parquet (for replay)
```

For NautilusTrader, this is what `TradingNode` does end-to-end: it wires the
venue adapter (Binance, Hyperliquid, Coinbase, etc.) into the message bus,
exposes `OrderBookDeltas` to your `Strategy`, and routes orders out the
configured adapter. The sibling `nautilus-trader` skill bundles the canonical
Hyperliquid mainnet wiring as a runnable live-trading reference of its own
(including the Hyperliquid SDK patch documented there) — open that skill for the
runnable file; it does not live in this skill.

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
