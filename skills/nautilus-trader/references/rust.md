# NautilusTrader — Rust Crate API

Cross-checked against:
- Context7 `/websites/nautilustrader_io_core-latest` (21,810 snippets) — Rust framework docs
- Auggie / Augment Code on `HyperFrequency/nautilus_trader` `develop` branch — `docs/how_to/write_rust_strategy.md`, `crates/trading/src/macros.rs`, `crates/common/src/actor/data_actor.rs`, `crates/backtest/tests/backtest_node.rs`, `crates/backtest/src/engine.rs`
- Live docs: <https://nautilustrader.io/docs/core-latest/>

> ⚠ The Rust API is still stabilizing. Context7 shows `add_actor` / `add_strategy` etc. as `todo!()` placeholders in the engine source; Auggie shows working implementations on `develop`. When porting strategy code, verify the current state of `crates/backtest/src/engine.rs` on the branch you're building against.

---

## 1. Crate layout

The user-facing Rust API spans three crates:

| Crate | Purpose | Key items |
| --- | --- | --- |
| `nautilus_common` | Cross-cutting types incl. the `DataActor` trait | `actor::DataActor`, `actor::DataActorCore`, `Component` |
| `nautilus_trading` | Strategy layer on top of actors | `strategy::Strategy`, `strategy::StrategyConfig`, `strategy::StrategyCore`, the `nautilus_strategy!` macro |
| `nautilus_backtest` | Backtest engine + node | `BacktestEngine`, `BacktestEngineConfig`, `BacktestNode`, `BacktestRunConfig` |
| `nautilus_model` | Domain types shared by all | `data::QuoteTick`, `data::Bar`, `enums::OrderSide`, `identifiers::{InstrumentId, StrategyId, Venue}`, `types::Quantity` |

---

## 2. Actor (Rust)

Implement the `DataActor` trait. Subscribe to data in `on_start`, handle events in typed handlers. Defaults are provided for every method; override what you need.

```rust
use nautilus_common::actor::DataActor;
use nautilus_model::{
    data::QuoteTick,
    identifiers::InstrumentId,
};

pub struct QuoteCounter {
    core: DataActorCore,
    instrument_id: InstrumentId,
    quote_count: u64,
}

impl DataActor for QuoteCounter {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }

    fn on_quote(&mut self, _quote: &QuoteTick) -> anyhow::Result<()> {
        self.quote_count += 1;
        Ok(())
    }
}
```

### Handler reference (subset)

The `DataActor` trait provides default impls for **all** of these; override only what you need.

| Handler | Fires on |
| --- | --- |
| `on_start`, `on_stop`, `on_resume`, `on_reset`, `on_dispose`, `on_degrade`, `on_fault` | Lifecycle transitions |
| `on_save`, `on_load` | State persistence |
| `on_time_event(event: &TimeEvent)` | Timer fired |
| `on_data(data: &dyn Any)` | Custom typed data |
| `on_instrument`, `on_instrument_status`, `on_instrument_close` | Instrument metadata changes |
| `on_book`, `on_book_deltas` | Order book updates |
| `on_quote`, `on_trade`, `on_bar` | Market data |
| `on_mark_price`, `on_index_price`, `on_funding_rate` | Perp/derivatives marks |
| `on_signal` | Custom signal events |
| `on_block`, `on_pool`, `on_pool_swap`, `on_pool_liquidity_update` | On-chain events |
| `on_historical_*` | Historical-data responses (paired with `subscribe_*` requests) |

Subscription methods (call from `on_start`):

- `subscribe_quotes(instrument_id, client_id, params)`
- `subscribe_trades(instrument_id, client_id, params)`
- `subscribe_bars(bar_type, client_id, params)`
- `subscribe_book_deltas(...)`, `subscribe_instruments(venue, ...)`, etc.

---

## 3. Strategy (Rust)

A strategy is an actor with order management. It owns a `StrategyCore` (not `DataActorCore`); the `StrategyCore` wraps `DataActorCore` and adds an `OrderFactory`, `OrderManager`, and portfolio integration.

```rust
use nautilus_common::actor::DataActor;
use nautilus_model::{
    data::QuoteTick,
    enums::OrderSide,
    identifiers::{InstrumentId, StrategyId},
    types::Quantity,
};
use nautilus_trading::{nautilus_strategy, strategy::{Strategy, StrategyConfig, StrategyCore}};

pub struct MyStrategy {
    core: StrategyCore,
    instrument_id: InstrumentId,
    trade_size: Quantity,
}

impl MyStrategy {
    pub fn new(instrument_id: InstrumentId) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("MY_STRAT-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            trade_size: Quantity::from("1.0"),
        }
    }
}

// Generates: Deref<Target=DataActorCore>, DerefMut, Strategy impl
// (core()/core_mut() accessors). Field defaults to `core`; pass a second
// arg for a different field name.
nautilus_strategy!(MyStrategy);

impl std::fmt::Debug for MyStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MyStrategy").finish()
    }
}

impl DataActor for MyStrategy {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }

    fn on_quote(&mut self, _quote: &QuoteTick) -> anyhow::Result<()> {
        let order = self.core.order_factory().market(
            self.instrument_id,
            OrderSide::Buy,
            self.trade_size,
            None, None, None, None, None, None, None,
        );
        self.submit_order(order, None, None)?;
        Ok(())
    }
}
```

### Order factory methods

`self.core.order_factory()` builds order objects:

- `market(instrument_id, side, qty, time_in_force?, reduce_only?, quote_quantity?, exec_algorithm?, exec_algorithm_params?, exec_spawn_id?, tags?, contingency_type?)`
- `limit(...)`, `stop_market(...)`, `stop_limit(...)`
- `market_if_touched(...)`, `limit_if_touched(...)`
- `trailing_stop_market(...)`

### Strategy methods (via the `Strategy` trait impl from the macro)

| Method | Action |
| --- | --- |
| `submit_order(order, position_id?, client_id?)` | Submit a new order |
| `submit_order_list(list, ...)` | Submit a list of contingent orders |
| `modify_order(...)` | Modify price, quantity, or trigger price |
| `cancel_order(client_order_id, ...)` | Cancel a specific order |
| `cancel_orders(filter, ...)` | Cancel a filtered set of orders |
| `cancel_all_orders(instrument_id, ...)` | Cancel all orders for an instrument |
| `close_position(position, ...)` | Close a position with a market order |
| `close_all_positions(instrument_id, ...)` | Close all open positions |

### Overriding Strategy hooks

Pass overrides as a block to the macro. The macro auto-generates `core()` / `core_mut()`; don't redefine them.

```rust
use nautilus_model::events::OrderRejected;

nautilus_strategy!(MyStrategy, {
    fn on_order_rejected(&mut self, event: OrderRejected) {
        log::warn!("Order rejected: {}", event.reason);
    }
});
```

For a custom core field name:

```rust
pub struct MyStrategy {
    strat_core: StrategyCore,
    // ...
}

nautilus_strategy!(MyStrategy, strat_core, {
    fn external_order_claims(&self) -> Option<Vec<InstrumentId>> { None }
});
```

---

## 4. Backtest (Rust)

Two patterns, matching the Python side.

### (a) Direct `BacktestEngine`

```rust
use nautilus_backtest::engine::{BacktestEngine, BacktestEngineConfig};

let config = BacktestEngineConfig::default();
let mut engine = BacktestEngine::new(config)?;

// (API in flux — verify add_venue/add_instrument/add_data/add_strategy
// against the current branch; see warning at top of file.)
engine.add_strategy(/* strategy */);
engine.run();
```

### (b) Config-driven `BacktestNode`

```rust
use nautilus_backtest::node::BacktestNode;
use nautilus_backtest::config::BacktestRunConfig;

let configs: Vec<BacktestRunConfig> = vec![/* ... */];
let node = BacktestNode::new(configs)?;
// node.run() / node.results()
```

`BacktestNode::new` returns an `Err` if `configs` is empty — see `crates/backtest/tests/backtest_node.rs::test_new_rejects_empty_configs`.

### Putting it together

```rust
use nautilus_backtest::engine::{BacktestEngine, BacktestEngineConfig};
use nautilus_common::actor::DataActor;
use nautilus_model::{data::QuoteTick, identifiers::InstrumentId};
use nautilus_trading::{nautilus_strategy, strategy::{StrategyConfig, StrategyCore}};

pub struct CountingStrategy {
    core: StrategyCore,
    instrument_id: InstrumentId,
    quote_count: u64,
}

nautilus_strategy!(CountingStrategy);

impl std::fmt::Debug for CountingStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CountingStrategy").finish()
    }
}

impl DataActor for CountingStrategy {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }
    fn on_quote(&mut self, _quote: &QuoteTick) -> anyhow::Result<()> {
        self.quote_count += 1;
        Ok(())
    }
}

fn main() -> anyhow::Result<()> {
    let mut engine = BacktestEngine::new(BacktestEngineConfig::default())?;
    // engine.add_venue(...); engine.add_instrument(...); engine.add_data(...);
    // engine.add_strategy(Box::new(CountingStrategy { ... }));
    engine.run();
    Ok(())
}
```

---

## 5. Reference reading

Canonical upstream files for the Rust API (paths on the `develop` branch):

- `docs/how_to/write_rust_actor.md` — actor walkthrough
- `docs/how_to/write_rust_strategy.md` — strategy walkthrough (basis for §3 above)
- `docs/how_to/run_rust_backtest.md` — `BacktestEngine` / `BacktestNode` walkthrough
- `docs/how_to/run_rust_live_trading.md` — `LiveNode` setup
- `docs/concepts/rust.md` — concept overview
- `crates/trading/src/macros.rs` — `nautilus_strategy!` macro definition
- `crates/common/src/actor/data_actor.rs` — the `DataActor` trait
- `crates/trading/src/strategy/mod.rs` — `Strategy` trait + `StrategyCore`
- `crates/backtest/src/engine.rs` — `BacktestEngine`
- `crates/backtest/tests/backtest_engine.rs` — working test fixtures with full impls (`SnapshotNettingFlip`, `CascadingStopStrategy`, `BarSubscriberStrategy`)
- `crates/backtest/tests/backtest_node.rs` — `BacktestNode` usage
- `crates/trading/src/examples/strategies/ema_cross/` — full EmaCross example
- `crates/trading/src/examples/strategies/grid_mm/` — grid market-maker example

Live API docs: <https://nautilustrader.io/docs/core-latest/nautilus_common/actor/data_actor/trait.DataActor.html> and <https://nautilustrader.io/docs/core-latest/nautilus_backtest/engine/struct.BacktestEngine.html>.

---

Last cross-checked: 2026-05-20.
