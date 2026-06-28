# Canonical example: Multi-timeframe EMA cross

This file is the reference implementation that every other file in this skill assumes
you have read. The strategy is identical across all eight versions; only the
representation changes.

## Contents

- [Strategy specification](#strategy-specification)
- [1. Basic Python (pandas + numpy)](#1-basic-python-pandas--numpy)
- [2. vectorbt](#2-vectorbt)
- [3. NautilusTrader (Python)](#3-nautilustrader-python)
- [4. NautilusTrader (Rust)](#4-nautilustrader-rust)
- [5. Pine Script v6](#5-pine-script-v6)
- [6. C++](#6-c)
- [7. Blog-post extrapolation (natural language)](#7-blog-post-extrapolation-natural-language)
- [8. Academic-paper extrapolation](#8-academic-paper-extrapolation)
- [How to use this file when translating](#how-to-use-this-file-when-translating)

## Strategy specification

- **Instrument:** BTC/USDT perpetual (single symbol).
- **Bars:** 5-minute execution timeframe, 1-hour trend-filter timeframe.
- **Indicators:**
  - 5m fast EMA, period 10
  - 5m slow EMA, period 30
  - 1h trend EMA, period 50
- **Long entry:** on the *close* of a 5m bar where:
  1. fast EMA crosses above slow EMA on 5m, **and**
  2. the most recent *closed* 1h bar's close is above its 1h EMA(50).
- **Long exit:** on the close of a 5m bar where fast EMA crosses below slow EMA on 5m,
  **or** the most recent closed 1h bar's close drops below its 1h EMA(50).
- **Direction:** long-only for the example. Short side is symmetric and omitted for
  clarity.
- **Sizing:** fixed notional, 1 unit per entry. (Real strategies size by risk; the
  example keeps sizing trivial so the framework comparison is the focus.)
- **Fills:** at the next bar's open after a signal. This avoids the look-ahead trap of
  filling on the bar that produced the signal.
- **Warmup:** drop the first `max(slow_period, trend_period * 12)` 5m bars so all EMAs
  are stable before the first possible signal.

The two non-obvious behaviors a translator must preserve:

1. **MTF alignment without lookahead.** The 1h trend filter must use the *last closed*
   1h bar at the moment of the 5m decision. Naive joins leak the future.
2. **Bar-close decision, next-bar-open fill.** Many backtest frameworks default to one
   or the other; if you don't pin it explicitly, the same logic produces different
   equity curves across formats.

---

## 1. Basic Python (pandas + numpy)

```python
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def mtf_ema_cross(bars_5m: pd.DataFrame, bars_1h: pd.DataFrame) -> pd.DataFrame:
    """
    bars_5m, bars_1h: DataFrames indexed by UTC timestamp with columns
    ['open', 'high', 'low', 'close', 'volume'].
    Returns bars_5m with added columns: signal (-1/0/1), position, entry_price, pnl.
    """
    fast = ema(bars_5m["close"], 10)
    slow = ema(bars_5m["close"], 30)
    trend = ema(bars_1h["close"], 50)

    # Last *closed* 1h bar at the time of each 5m bar. merge_asof with
    # direction='backward' grabs the most recent prior 1h bar; we then shift by
    # one 1h bar to ensure it is closed (not the in-progress one).
    trend_df = pd.DataFrame({"trend": trend, "trend_close": bars_1h["close"]})
    trend_df = trend_df.shift(1)  # last *closed* 1h bar
    aligned = pd.merge_asof(
        bars_5m.reset_index().rename(columns={"index": "ts"}),
        trend_df.reset_index().rename(columns={"index": "ts"}),
        on="ts",
        direction="backward",
    ).set_index("ts")

    long_filter = aligned["trend_close"] > aligned["trend"]
    cross_up = (fast > slow) & (fast.shift(1) <= slow.shift(1))
    cross_dn = (fast < slow) & (fast.shift(1) >= slow.shift(1))

    entry = cross_up & long_filter
    exit_ = cross_dn | ~long_filter

    position = np.zeros(len(bars_5m), dtype=int)
    in_pos = 0
    for i in range(1, len(bars_5m)):
        if in_pos == 0 and entry.iat[i]:
            in_pos = 1
        elif in_pos == 1 and exit_.iat[i]:
            in_pos = 0
        position[i] = in_pos

    # Fill at next bar's open
    fill_price = bars_5m["open"].shift(-1)
    pnl = (fill_price.diff().fillna(0)) * pd.Series(position, index=bars_5m.index).shift(1).fillna(0)

    out = bars_5m.copy()
    out["fast"] = fast
    out["slow"] = slow
    out["trend"] = aligned["trend"]
    out["entry"] = entry
    out["exit"] = exit_
    out["position"] = position
    out["pnl"] = pnl
    return out
```

### Diff vs source
This *is* the source for every diff below. The two things to notice that every
translation must preserve:
- `trend_df.shift(1)` — the closed-1h-bar guarantee. Without it the strategy peeks at the
  in-progress 1h bar and overstates returns.
- The position update loop fills at `bars_5m["open"].shift(-1)`, i.e. next-bar open. The
  rest of the implementations encode this same convention with whatever knob the
  framework provides.

---

## 2. vectorbt

```python
import numpy as np
import pandas as pd
import vectorbt as vbt


def mtf_ema_cross_vbt(bars_5m: pd.DataFrame, bars_1h: pd.DataFrame):
    fast = vbt.MA.run(bars_5m["close"], window=10, ewm=True).ma
    slow = vbt.MA.run(bars_5m["close"], window=30, ewm=True).ma
    trend = vbt.MA.run(bars_1h["close"], window=50, ewm=True).ma

    # Use the previous closed 1h bar at every 5m timestamp.
    trend_closed = trend.shift(1)
    close_1h_closed = bars_1h["close"].shift(1)
    long_filter_1h = (close_1h_closed > trend_closed).astype(float)

    # Reindex 1h filter onto 5m index with forward-fill so each 5m bar sees the
    # last closed 1h state.
    long_filter = long_filter_1h.reindex(bars_5m.index, method="ffill").fillna(0).astype(bool)

    cross_up = fast.vbt.crossed_above(slow)
    cross_dn = fast.vbt.crossed_below(slow)

    entries = cross_up & long_filter
    exits = cross_dn | ~long_filter

    pf = vbt.Portfolio.from_signals(
        close=bars_5m["close"],
        entries=entries,
        exits=exits,
        price=bars_5m["open"].shift(-1),  # fill at next bar's open
        freq="5T",
        init_cash=10_000,
        size=1.0,
        size_type="amount",
        fees=0.0005,
        slippage=0.0,
    )
    return pf
```

### Diff vs basic Python
- **Indicators are batched.** `vbt.MA.run` is vectorized across the whole series and can
  itself accept arrays of windows for sweeps. The basic-Python version uses a single
  pandas EWM call per indicator.
- **Crosses are first-class.** `fast.vbt.crossed_above(slow)` replaces the manual
  `(fast > slow) & (fast.shift(1) <= slow.shift(1))` idiom. Same semantics, less room for
  off-by-one bugs.
- **MTF alignment is `reindex(method="ffill")`** instead of `merge_asof`. Both produce
  "last closed 1h value at each 5m bar" *as long as* you pre-shift the 1h series. The
  pre-shift is the part you cannot omit.
- **The position loop disappears.** `Portfolio.from_signals` consumes entry/exit boolean
  arrays directly and handles the in/out state machine. This is the entire reason
  vectorbt exists: parameter sweeps run thousands of these in parallel without a Python
  loop in sight.
- **Fill timing is set by `price=bars_5m["open"].shift(-1)`.** vectorbt defaults to
  filling at the same bar's `close`; that default is wrong for any strategy that
  decides on bar-close. Always pass `price` explicitly.
- **Semantic risk:** vectorbt's signal-shift conventions trip people. If you pass
  `entries` already shifted by 1, you double-shift. The rule: emit signals at the bar
  they fire on, and let `price=open.shift(-1)` handle the fill timing.

---

## 3. NautilusTrader (Python)

This version follows the current upstream conventions confirmed against
`nautechsystems/nautilus_trader@develop` and the HyperFrequency fork
(`HF-nautilus_trader@develop`): indicators are *registered* to bar types and update
themselves automatically; position state is queried through `self.portfolio`; warmup is
gated by `self.indicators_initialized()`; instruments are fetched from `self.cache` in
`on_start`.

```python
from decimal import Decimal

from nautilus_trader.config import StrategyConfig, PositiveInt
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


class MTFEmaCrossConfig(StrategyConfig, frozen=True):
    """
    Multi-timeframe EMA cross configuration.

    Example bar types (constructed via BarType.from_str at the call site):
        bar_type_5m = "BTCUSDT-PERP.BINANCE-5-MINUTE-LAST-EXTERNAL"
        bar_type_1h = "BTCUSDT-PERP.BINANCE-1-HOUR-LAST-EXTERNAL"
    """
    instrument_id: InstrumentId
    bar_type_5m: BarType
    bar_type_1h: BarType
    fast_period: PositiveInt = 10
    slow_period: PositiveInt = 30
    trend_period: PositiveInt = 50
    trade_size: Decimal = Decimal("1")
    close_positions_on_stop: bool = True


class MTFEmaCross(Strategy):
    """
    Long-only multi-timeframe EMA cross.

    - Entry: 5m fast EMA crosses above 5m slow EMA AND last closed 1h bar
      sits above the 1h trend EMA.
    - Exit: opposite 5m cross, OR 1h trend filter flips against the position.
    """

    def __init__(self, config: MTFEmaCrossConfig) -> None:
        super().__init__(config)
        self.instrument: Instrument | None = None

        # Indicators are registered to specific bar types in on_start, so each
        # timeframe drives only its own indicators — no manual update calls,
        # no MTF alignment code.
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)
        self.trend_ema = ExponentialMovingAverage(config.trend_period)

        # Local state kept only for things the framework does not track for us.
        self._prev_fast: float | None = None
        self._prev_slow: float | None = None
        self._trend_ok: bool = False  # last closed 1h close > 1h EMA(50)?

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument for {self.config.instrument_id}")
            self.stop()
            return

        # Register each indicator against its own bar type. Nautilus will then
        # auto-update fast/slow only on 5m bars and trend only on 1h bars.
        self.register_indicator_for_bars(self.config.bar_type_5m, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type_5m, self.slow_ema)
        self.register_indicator_for_bars(self.config.bar_type_1h, self.trend_ema)

        # Subscribe to both timeframes for the same instrument.
        self.subscribe_bars(self.config.bar_type_5m)
        self.subscribe_bars(self.config.bar_type_1h)

    def on_bar(self, bar: Bar) -> None:
        # 1h branch: refresh the trend filter. Indicators have already been
        # updated by the framework before this callback fires.
        if bar.bar_type == self.config.bar_type_1h:
            if self.trend_ema.initialized:
                self._trend_ok = float(bar.close) > self.trend_ema.value
            return

        # 5m branch: trade.
        if not self.indicators_initialized():
            return  # all registered indicators must be warm

        # Cross detection uses prev/current samples since registered
        # indicators expose only the latest value.
        cross_up = (
            self._prev_fast is not None
            and self._prev_slow is not None
            and self._prev_fast <= self._prev_slow
            and self.fast_ema.value > self.slow_ema.value
        )
        cross_dn = (
            self._prev_fast is not None
            and self._prev_slow is not None
            and self._prev_fast >= self._prev_slow
            and self.fast_ema.value < self.slow_ema.value
        )

        if cross_up and self._trend_ok and self.portfolio.is_flat(self.config.instrument_id):
            self._enter_long()
        elif (cross_dn or not self._trend_ok) and self.portfolio.is_net_long(
            self.config.instrument_id
        ):
            self.close_all_positions(self.config.instrument_id)

        self._prev_fast = self.fast_ema.value
        self._prev_slow = self.slow_ema.value

    def _enter_long(self) -> None:
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.config.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        if self.config.close_positions_on_stop:
            self.close_all_positions(self.config.instrument_id)
        self.unsubscribe_bars(self.config.bar_type_5m)
        self.unsubscribe_bars(self.config.bar_type_1h)

    def on_reset(self) -> None:
        self.fast_ema.reset()
        self.slow_ema.reset()
        self.trend_ema.reset()
        self._prev_fast = None
        self._prev_slow = None
        self._trend_ok = False
```

### Diff vs basic Python
- **Event-driven, not vectorized.** `on_bar` fires once per closed bar. There is no
  `DataFrame`; state lives on `self`. This is the model that ports 1:1 to live trading
  without changing a line of strategy logic.
- **MTF without joins.** Subscribe to *both* bar types and route on `bar.bar_type`. The
  1h branch refreshes `self._trend_ok` whenever a 1h bar closes; the 5m branch reads it.
  No alignment code is needed, and no lookahead is possible — `on_bar` only fires after
  a bar closes.
- **Indicators auto-update via `register_indicator_for_bars`.** Each indicator is bound
  to a specific bar type at start, and Nautilus updates it before `on_bar` runs. This
  replaces the basic-Python `ewm(...).mean()` *and* the manual `indicator.update_raw(...)`
  pattern. If you find yourself calling `update_raw` inside `on_bar`, you're either
  fighting the framework or your indicator is unregistered — go back and register it.
- **Warmup is one call.** `self.indicators_initialized()` returns true once *every*
  registered indicator has its window. No per-indicator `.initialized` checks.
- **Position state via `self.portfolio`.** `self.portfolio.is_flat(...)` and
  `self.portfolio.is_net_long(...)` are the upstream-recommended source of truth, used
  in every shipped EMA-cross example in `nautilus_trader/examples/strategies/`. The
  cache also exposes positions, but the portfolio API is the cleaner read path inside a
  strategy.
- **Cross detection uses two-sample state** (`_prev_fast`, `_prev_slow`) rather than a
  shifted Series. Same logic expressed pointwise — this is the canonical pattern for
  any registered indicator that exposes only the current value.
- **Fills happen via the matching engine**, not by indexing into `open.shift(-1)`. The
  default sim venue fills the next bar; if you want a different model, configure the
  venue, not the strategy.
- **Lifecycle hooks (`on_start`/`on_stop`/`on_reset`)** are mandatory in any production
  strategy. `on_start` fetches the instrument from the cache (and bails if missing),
  `on_stop` flattens, `on_reset` clears indicator and local state for parameter sweeps.
- **Semantic risk:** `BarType` strings encode timeframe AND aggregation source. The
  trend filter must use a `LAST-EXTERNAL` (or matching) 1h bar from the same instrument
  as the 5m source, otherwise you are filtering on a different price stream than you're
  trading. Construct both via `BarType.from_str(f"{instrument_id}-5-MINUTE-LAST-EXTERNAL")`
  / `f"{instrument_id}-1-HOUR-LAST-EXTERNAL"` and verify by logging at start.

---

## 4. NautilusTrader (Rust)

The Rust strategy API is built around `StrategyCore` (held inside your struct) and the
`DataActor` trait (which delivers data callbacks). This shape is taken directly from
`docs/how_to/write_rust_strategy.md` in `nautechsystems/nautilus_trader@develop`. Verify
the exact trait method names against the version you build against — the Rust API has
churned more than the Python API and a few methods may be renamed by the time you read
this.

```rust
use nautilus_common::actor::DataActor;
use nautilus_indicators::average::ema::ExponentialMovingAverage;
use nautilus_model::{
    data::{Bar, BarType},
    enums::{OrderSide, TimeInForce},
    identifiers::{InstrumentId, StrategyId},
    types::Quantity,
};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

pub struct MtfEmaCross {
    core: StrategyCore,
    instrument_id: InstrumentId,
    bar_type_5m: BarType,
    bar_type_1h: BarType,
    fast_ema: ExponentialMovingAverage,
    slow_ema: ExponentialMovingAverage,
    trend_ema: ExponentialMovingAverage,
    prev_fast: Option<f64>,
    prev_slow: Option<f64>,
    trend_ok: bool,
    trade_size: Quantity,
}

impl MtfEmaCross {
    pub fn new(
        instrument_id: InstrumentId,
        bar_type_5m: BarType,
        bar_type_1h: BarType,
        fast_period: usize,
        slow_period: usize,
        trend_period: usize,
    ) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("MTF_EMA_CROSS-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };

        Self {
            core: StrategyCore::new(config),
            instrument_id,
            bar_type_5m,
            bar_type_1h,
            fast_ema: ExponentialMovingAverage::new(fast_period, None).unwrap(),
            slow_ema: ExponentialMovingAverage::new(slow_period, None).unwrap(),
            trend_ema: ExponentialMovingAverage::new(trend_period, None).unwrap(),
            prev_fast: None,
            prev_slow: None,
            trend_ok: false,
            trade_size: Quantity::from("1.0"),
        }
    }
}

impl DataActor for MtfEmaCross {
    fn on_start(&mut self) {
        // Register indicators against their respective bar types and subscribe.
        // The exact method names on StrategyCore (register_indicator_for_bars,
        // subscribe_bars) match the Python surface; if your build pins an older
        // tag, check the trait definition.
        self.core
            .register_indicator_for_bars(&self.bar_type_5m, &mut self.fast_ema);
        self.core
            .register_indicator_for_bars(&self.bar_type_5m, &mut self.slow_ema);
        self.core
            .register_indicator_for_bars(&self.bar_type_1h, &mut self.trend_ema);

        self.core.subscribe_bars(&self.bar_type_5m);
        self.core.subscribe_bars(&self.bar_type_1h);
    }

    fn on_bar(&mut self, bar: &Bar) {
        // 1h branch: refresh trend filter (indicator already updated by core).
        if bar.bar_type == self.bar_type_1h {
            if self.trend_ema.initialized() {
                self.trend_ok = bar.close.as_f64() > self.trend_ema.value();
            }
            return;
        }

        // 5m branch.
        if !(self.fast_ema.initialized() && self.slow_ema.initialized()) {
            self.prev_fast = Some(self.fast_ema.value());
            self.prev_slow = Some(self.slow_ema.value());
            return;
        }

        let cross_up = matches!(
            (self.prev_fast, self.prev_slow),
            (Some(pf), Some(ps)) if pf <= ps && self.fast_ema.value() > self.slow_ema.value()
        );
        let cross_dn = matches!(
            (self.prev_fast, self.prev_slow),
            (Some(pf), Some(ps)) if pf >= ps && self.fast_ema.value() < self.slow_ema.value()
        );

        let is_flat = self.core.portfolio_is_flat(&self.instrument_id);
        let is_long = self.core.portfolio_is_net_long(&self.instrument_id);

        if cross_up && self.trend_ok && is_flat {
            self.submit_market(OrderSide::Buy);
        } else if (cross_dn || !self.trend_ok) && is_long {
            self.core.close_all_positions(&self.instrument_id);
        }

        self.prev_fast = Some(self.fast_ema.value());
        self.prev_slow = Some(self.slow_ema.value());
    }

    fn on_stop(&mut self) {
        self.core.cancel_all_orders(&self.instrument_id);
        self.core.close_all_positions(&self.instrument_id);
    }
}

impl MtfEmaCross {
    fn submit_market(&mut self, side: OrderSide) {
        let order = self.core.order_factory().market(
            self.instrument_id,
            side,
            self.trade_size,
            TimeInForce::Gtc,
        );
        self.core.submit_order(order);
    }
}
```

### Diff vs basic Python
- **Same event model as Nautilus Python**, transposed onto Rust traits. The strategy
  *holds* a `StrategyCore` rather than inheriting from a base class — Rust has no
  inheritance, so composition + the `DataActor` trait fill the same role.
- **`DataActor` trait callbacks (`on_start`, `on_bar`, `on_stop`)** are the Rust
  equivalent of the Python `Strategy` lifecycle hooks. Method names match 1:1 with the
  Python API on purpose.
- **Indicators are registered the same way** as in Python — `register_indicator_for_bars`
  on the core, against a specific bar type. Each timeframe drives only its registered
  indicators, and the core updates them before `on_bar` fires.
- **Position state via the core's portfolio helpers** (`portfolio_is_flat`,
  `portfolio_is_net_long`). No local `in_position` flag, because real fills can be
  partial, rejected, or delayed; the core's view is the source of truth.
- **Order construction goes through `self.core.order_factory().market(...)`**, mirroring
  the Python `self.order_factory.market(...)` call. There is also a builder API on
  `MarketOrder` itself for cases where you need fields the factory doesn't expose; the
  factory is the right default.
- **Why translate to Rust at all?** Lower per-event latency and predictable allocation
  on the hot path. If your strategy fits comfortably in the Python event loop, do not
  port it to Rust just for speed — port it when latency variance starts mattering for
  fills, or when you need to share the engine with non-Python downstream consumers.
- **Semantic risk #1 — API drift.** The Rust strategy surface is younger than the Python
  one and has been moving. Always pin the `nautilus-trading` and `nautilus-indicators`
  crate versions and re-run `docs-dual-lookup` against the tag you actually compile
  against before shipping a production strategy. If a method shown above no longer
  exists, prefer the closest current trait method on `DataActor` or `StrategyCore`
  rather than guessing.
- **Semantic risk #2 — fixed-precision prices.** `bar.close.as_f64()` is fine for
  indicator math, *not* for sizing or PnL. Real strategies keep prices in the native
  fixed type and only convert at indicator boundaries. Floating-point EMAs will also
  drift a few ULPs from the Python version over millions of bars; if you need
  bit-identical agreement across languages, switch to fixed-point indicators.

---

## 5. Pine Script v6

```pinescript
//@version=6
strategy("MTF EMA Cross (5m + 1h)", overlay=true,
     default_qty_type=strategy.fixed, default_qty_value=1,
     process_orders_on_close=false, calc_on_every_tick=false)

fastLen  = input.int(10, "Fast EMA")
slowLen  = input.int(30, "Slow EMA")
trendLen = input.int(50, "Trend EMA (1h)")

fast = ta.ema(close, fastLen)
slow = ta.ema(close, slowLen)

// request.security with lookahead_off and the [1] index gives the last *closed*
// 1h bar — this is the v6 idiom for leak-free MTF.
trend1h     = request.security(syminfo.tickerid, "60", ta.ema(close, trendLen)[1],
     lookahead=barmerge.lookahead_off)
close1h     = request.security(syminfo.tickerid, "60", close[1],
     lookahead=barmerge.lookahead_off)
trendOk     = close1h > trend1h

crossUp = ta.crossover(fast, slow)
crossDn = ta.crossunder(fast, slow)

if crossUp and trendOk and strategy.position_size == 0
    strategy.entry("L", strategy.long)

if (crossDn or not trendOk) and strategy.position_size > 0
    strategy.close("L")

plot(fast, "Fast", color=color.aqua)
plot(slow, "Slow", color=color.orange)
```

### Diff vs basic Python
- **MTF is `request.security`**, and the leak-free recipe is `[1]` *inside* the security
  call combined with `lookahead=barmerge.lookahead_off`. Either alone is not enough; this
  is the single most common Pine v6 bug in MTF strategies.
- **`process_orders_on_close=false` + `calc_on_every_tick=false`** keeps the backtest on
  bar-close decisions and next-bar fills, matching the Python convention. Flip either
  and the equity curve changes.
- **No explicit position state.** `strategy.position_size` is the source of truth. Pine
  hides the state machine.
- **No warmup logic needed** in user code — Pine evaluates from the first bar where the
  series is `na`-free. If you want stricter warmup, gate entries on `bar_index > N`.
- **Semantic risk:** Pine has historically had silent lookahead issues in MTF. Treat any
  Pine MTF strategy as suspect until you've verified on the chart that signals only
  appear after the higher-timeframe bar has closed. This is the place I'd recommend the
  user spot-check visually before trusting any backtest.

---

## 6. C++

```cpp
// Self-contained header. No exchange wiring; the point is to show the
// inner-loop shape that an embedded engine would use.
#pragma once
#include <cstddef>
#include <optional>
#include <string>

struct Bar {
    long long ts_ns;     // bar close timestamp
    double open, high, low, close, volume;
};

class Ema {
public:
    explicit Ema(std::size_t period)
        : alpha_(2.0 / (static_cast<double>(period) + 1.0)) {}

    void update(double x) {
        if (!initialized_) {
            value_ = x;
            initialized_ = true;
        } else {
            value_ = alpha_ * x + (1.0 - alpha_) * value_;
        }
    }
    bool initialized() const { return initialized_; }
    double value() const { return value_; }

private:
    double alpha_;
    double value_ = 0.0;
    bool initialized_ = false;
};

enum class Side { Buy, Sell, None };

class MtfEmaCross {
public:
    MtfEmaCross(std::size_t fast_p, std::size_t slow_p, std::size_t trend_p)
        : fast_(fast_p), slow_(slow_p), trend_(trend_p) {}

    // Call with each closed bar. tag must be "5m" or "1h".
    Side on_bar(const Bar& bar, const std::string& tag) {
        if (tag == "1h") {
            trend_.update(bar.close);
            if (trend_.initialized()) trend_ok_ = bar.close > trend_.value();
            return Side::None;
        }
        // 5m branch
        fast_.update(bar.close);
        slow_.update(bar.close);
        if (!(fast_.initialized() && slow_.initialized())) {
            prev_fast_ = fast_.value();
            prev_slow_ = slow_.value();
            return Side::None;
        }

        const bool cross_up =
            prev_fast_.has_value() && *prev_fast_ <= *prev_slow_ &&
            fast_.value() > slow_.value();
        const bool cross_dn =
            prev_fast_.has_value() && *prev_fast_ >= *prev_slow_ &&
            fast_.value() < slow_.value();

        Side action = Side::None;
        if (!in_position_ && cross_up && trend_ok_) {
            in_position_ = true;
            action = Side::Buy;
        } else if (in_position_ && (cross_dn || !trend_ok_)) {
            in_position_ = false;
            action = Side::Sell;
        }
        prev_fast_ = fast_.value();
        prev_slow_ = slow_.value();
        return action;
    }

private:
    Ema fast_, slow_, trend_;
    std::optional<double> prev_fast_;
    std::optional<double> prev_slow_;
    bool trend_ok_ = false;
    bool in_position_ = false;
};
```

### Diff vs basic Python
- **No allocations on the hot path.** Indicators are stack-resident POD-ish objects with
  scalar state. This is what you translate to when the Python or Rust Nautilus version
  isn't fast enough — usually only true for sub-millisecond paths.
- **Routing by `tag` string** is a placeholder. A real engine routes by symbol/timeframe
  ID through a switch or jump table; the string compare is here so the example reads
  cleanly next to the others.
- **No order objects** — `on_bar` returns a `Side` and the caller is responsible for
  emitting the actual exchange message. Keeping side-effects out of the strategy core is
  what makes a C++ strategy testable.
- **Same 1h gating, same cross logic, same prev-sample state machine** as the Rust and
  Python Nautilus versions. The shape is portable; only the host changes.
- **Semantic risk:** floating-point EMAs drift compared to fixed-point implementations
  in the other languages. Over millions of bars the indicator values diverge by a few
  ULPs. If you need bit-identical behavior across languages for compliance reasons,
  switch to a fixed-point or decimal indicator.

---

## 7. Blog-post extrapolation (natural language)

### A simple multi-timeframe trend filter, in plain English

The idea is unflashy: only take a fast trend signal if the slow trend agrees. We watch
five-minute bars on BTC for a quick momentum cue — a 10-period EMA crossing above a
30-period EMA — but we only act when the one-hour chart is also pointed up, defined as
the most recent closed hourly bar trading above its 50-period EMA.

The two-timeframe gate is the whole point. A 5m crossover on its own gives you a lot of
trades and a lot of chop. Demanding that the 1h trend agree filters out most of the
whipsaws and leaves you with positions that at least start with the wind at their
back. We exit on the opposite 5m cross or the moment the 1h trend flips against us,
whichever comes first.

Two details that look small but matter a lot in practice:

1. **Always read the *last closed* hourly bar.** If you peek at the still-forming bar,
   your backtest will look amazing and your live trading will look nothing like it. Every
   serious framework has a knob for this; use it.
2. **Decide on bar close, fill on the next bar's open.** Otherwise you're implicitly
   assuming you can trade at the same price the indicator just used to make its
   decision, which is a free lunch nobody serves.

That's it. No magic, no overfitting story, just a trend filter on top of a crossover.
The interesting parts are everything around it: how you size, how you handle fees, and
how the same logic ports cleanly between your research notebook and your live engine.

### Faithfulness notes
- The "10/30/50" parameters and the "5m + 1h" pairing are taken directly from the spec
  at the top of this file.
- "Last closed bar" framing maps to the `shift(1)` / `[1]` / `_trend_ok` patterns in the
  code versions above.
- "Fill on the next bar's open" is the convention pinned by `open.shift(-1)` in pandas
  and vectorbt, and by the default sim venue in Nautilus.
- Nothing about why this *strategy* is good is asserted — the post deliberately stays
  agnostic about edge. Extrapolation should not invent claims the source code does not
  support.

---

## 8. Academic-paper extrapolation

### A two-timeframe exponential moving average crossover with a higher-timeframe trend filter

**Abstract.** We describe a long-only trading rule defined on two synchronized bar
series of the same instrument: a fast series sampled at five-minute intervals and a slow
series sampled at one-hour intervals. The rule emits an entry signal on the close of a
fast-series bar at which (i) a fast exponential moving average crosses above a slower
exponential moving average on the fast series, and (ii) the most recently closed
slow-series bar trades above its own exponential moving average. Exits are emitted on
the opposite fast-series cross or on a violation of the slow-series condition. We pin
all decisions to bar-close timestamps and all fills to the open of the immediately
subsequent fast-series bar in order to remove the look-ahead artifacts that otherwise
contaminate multi-timeframe backtests.

**1. Notation.** Let $`P^{(f)}_t`$ denote the close of the fast bar series at index $`t`$
and $`P^{(s)}_\tau`$ denote the close of the slow bar series at index $`\tau`$. Define
the exponential moving average $`\mathrm{EMA}_n[X_t] = \alpha X_t + (1-\alpha)
\mathrm{EMA}_n[X_{t-1}]`$ with $`\alpha = 2/(n+1)`$. Let $`\tau(t)`$ be the index of the
most recently *closed* slow-series bar at fast-bar time $`t`$.

**2. Signal.** Let
$`F_t = \mathrm{EMA}_{10}[P^{(f)}_t]`$, $`S_t = \mathrm{EMA}_{30}[P^{(f)}_t]`$, and
$`T_\tau = \mathrm{EMA}_{50}[P^{(s)}_\tau]`$. Define
$$
\text{entry}_t = \mathbb{1}\{F_{t-1} \le S_{t-1}\} \cdot \mathbb{1}\{F_t > S_t\} \cdot
                 \mathbb{1}\{P^{(s)}_{\tau(t)} > T_{\tau(t)}\},
$$
$$
\text{exit}_t  = \mathbb{1}\{F_{t-1} \ge S_{t-1}\} \cdot \mathbb{1}\{F_t < S_t\}
              \;\lor\; \mathbb{1}\{P^{(s)}_{\tau(t)} \le T_{\tau(t)}\}.
$$

**3. Execution model.** The agent holds at most one unit of inventory. Orders are
emitted at fast-bar close $`t`$ and filled at the next fast-bar open price $`O^{(f)}_{t+1}`$.
This decouples the decision price from the fill price, eliminating the trivial
look-ahead in which a backtest assumes execution at the same price the indicator just
consumed. The use of $`\tau(t)`$ for the *closed* slow bar — rather than the in-progress
one — is a second look-ahead control that is necessary for any multi-timeframe rule and
which we have observed to be omitted in informal implementations.

**4. Discussion.** The rule is presented without an empirical evaluation; it is intended
as a minimal canonical example for cross-framework strategy translation rather than as a
proposed alpha. Any backtest of this rule should report fees, slippage, and the warmup
window required for the slowest indicator (here $`50 \times 12 = 600`$ fast bars) before
admitting the first signal. We recommend reproducing the rule independently in at least
two frameworks with different execution-model assumptions and confirming agreement of
trade timestamps to the nearest fast bar.

### Faithfulness notes
- All notation is mechanically derived from the spec at the top of this file. No claims
  about profitability are made.
- The "look-ahead controls" in Section 3 are exactly the two semantic pitfalls flagged
  in the basic-Python diff: `shift(1)` on the slow series and `shift(-1)` on the fill
  price.
- The warmup formula $`50 \times 12`$ comes from the relationship between the 5m and 1h
  timeframes (12 five-minute bars per hour) and is taken from the spec.
- An academic write-up that did not have a real backtest would normally be a red flag;
  this version states that absence explicitly so the reader is not misled.

---

## How to use this file when translating

When the user asks for a translation, find the source format in the table of contents
above, find the target format, and use the patterns from each version. The diffs are
where the load-bearing knowledge lives — they describe the framework-specific semantic
risks you need to preserve. The actual code is just the carrier.
