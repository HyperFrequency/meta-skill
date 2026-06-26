---
title: NautilusTrader — translation reference
domain: software-engineering
confidence: medium
last_updated: 2026-04-20
---

# NautilusTrader reference

Event-driven backtest + live engine in Python and Rust. The mental
model is fundamentally different from vectorbt — you handle one bar
(or tick) at a time via callbacks, accumulate state between calls, and
submit orders through a broker abstraction.

## Live-lookup gate (mandatory)

Before emitting Nautilus code, verify the current API via Context7:
- Library ID: `/llmstxt/nautilus_trader` (when available) or resolve via
  `mcp__context7__resolve-library-id` with `libraryName="nautilus-trader"`.
- Cite the returned library ID in the translation's preamble.

For HF-forked nautilus-trader-hyperliquid (user has a fork at
`~/hyperfrequency/nautilus-trader-hyperliquid/`), use
`/deep-tool-wiki` — it has HF-specific curated docs for forked tools.

## Mental model

| Concept | Pine | Nautilus (Python/Rust) |
|---|---|---|
| Iteration | implicit (script runs per bar) | explicit `on_bar(bar)` / `on_event(event)` |
| State | `var` / `varip` | instance fields on the strategy class |
| Signals | boolean vars, `strategy.entry()` | `self.submit_order()` with typed Order |
| Indicators | `ta.ema(close, n)` | `ExponentialMovingAverage(n)` updated by `indicator.update_raw(close)` |
| Timing | bar-close (default) | depends on `BarSpec` + order type |

## Canonical Python skeleton

```python
from nautilus_trader.indicators.ema import ExponentialMovingAverage
from nautilus_trader.model.data import Bar
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.trading.strategy import Strategy

class EMACrossStrategy(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.fast = ExponentialMovingAverage(config.fast_period)
        self.slow = ExponentialMovingAverage(config.slow_period)
        self.prev_fast = None  # for crossover detection
        self.prev_slow = None

    def on_start(self):
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        close = bar.close.as_double()
        self.fast.update_raw(close)
        self.slow.update_raw(close)

        if not (self.fast.initialized and self.slow.initialized):
            self.prev_fast, self.prev_slow = self.fast.value, self.slow.value
            return

        cross_up = (self.fast.value > self.slow.value) and (self.prev_fast <= self.prev_slow)
        cross_dn = (self.fast.value < self.slow.value) and (self.prev_fast >= self.prev_slow)

        if cross_up:
            self.submit_order(MarketOrder(...side=OrderSide.BUY...))
        elif cross_dn:
            self.close_all_positions(self.instrument_id)

        # IMPORTANT: update prev values AFTER the comparison
        self.prev_fast, self.prev_slow = self.fast.value, self.slow.value
```

## Indicator library

Nautilus ships Wilder-correct indicators by default. Prefer the built-ins
over hand-rolled math:

- `ExponentialMovingAverage` — standard EMA (alpha = 2/(n+1))
- `WilderMovingAverage` — Wilder (alpha = 1/n) — for ATR, RSI
- `RelativeStrengthIndex` — uses Wilder smoothing
- `AverageTrueRange` — Wilder-smoothed ATR
- `BollingerBands` — biased stdev (ddof=0) — matches Pine
- `Stochastics`, `MACD`, `SimpleMovingAverage`, etc.

Only reach for manual numpy when a Nautilus indicator does not exist.
In that case, pass `adjust=False, ddof=0` and cite why the built-in
wasn't used in the Diff vs source section.

## Crossover detection — explicit prev state

Nautilus does not provide `ta.crossover`-equivalent accessors. Store
`prev_*` values in the strategy's instance fields and compare current
vs prior — update prev **after** the comparison to avoid eating the
crossover bar (same pitfall as C++; see `references/pinescript-v6.md`
Pitfall 4).

## Fill timing

`BarSpec(aggregation=BarAggregation.MINUTE, step=1, price_type=PriceType.LAST)`
+ `OrderType.MARKET` with `TimeInForce.GTC` — fills at the **next tick
after the bar that triggered the signal**. This differs from Pine's
default (next bar open) by typically a few ms.

If the Pine source assumes `process_orders_on_close=true`, match with
`BarSpec(... price_type=PriceType.LAST)` + order submission on
`on_bar` *after* updating indicators — but note the fill is still at
the next tick, not the bar close itself.

State the assumed fill timing in the Diff vs source section.

## Nautilus Rust vs Python

The Rust crate (`nautilus-core`, `nautilus-model`, `nautilus-common`,
`nautilus-execution`) is the production-grade path. Most user strategy
code lives in Python; Rust is used for custom indicators, execution
venues, or performance-critical features. When translating to Rust:

- Strategy struct holds indicator fields directly (not Box'd).
- `on_bar` becomes a trait method taking `&mut self` + `&Bar`.
- Indicator types are imported from `nautilus_indicators::*`.
- Order submission via the `ExecutionEngine` trait.
- Compile-time types (`Price`, `Quantity`, `InstrumentId`) replace
  Python's runtime checks.

Fewer Pro-patterns exist in Rust — most translations should default
to Python unless the user explicitly asks for Rust latency.

## Vault-curated knowledge

If the user has indexed nautilus docs in their vault, check first:
```
mcp__neuro-link-recursive__nlr_wiki_search
  query: "nautilus trader <specific concern>"
```

The HF fork `nautilus-trader-hyperliquid` has Hyperliquid-specific
patches; its deep-tool-wiki page is the authoritative source for
HL-related idioms.

## Anti-patterns specific to Nautilus

- **Don't call `self.fast.value` before `fast.initialized`** — returns
  stale zero. Gate on `initialized` for both MAs before comparing.
- **Don't update `prev_*` before the comparison** — same crossover
  bug as Pine/C++. Update after.
- **Don't hand-roll Wilder smoothing** — use `WilderMovingAverage`.
- **Don't skip `subscribe_bars()` in `on_start`** — `on_bar` never
  fires without it.
- **Don't conflate `Strategy.submit_order` with broker-specific APIs** —
  stick with the abstracted `OrderFactory.market()` / `.limit()`
  unless you have a live-venue reason.

## Source

- Primary: Context7 (resolve `nautilus-trader` library ID live per run)
- Secondary (HF-forked): `/deep-tool-wiki` for
  `nautilus-trader-hyperliquid`
- Validation: shakedown judge consortium runs
