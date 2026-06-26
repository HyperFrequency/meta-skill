# NautilusTrader — Curated API Quick Reference (Python)

> This file covers the **Python** API. For the **Rust crate API** (DataActor trait, Strategy trait + `nautilus_strategy!` macro, BacktestEngine + BacktestNode in Rust), see [`rust.md`](./rust.md).
>
> Authoritative source: **<https://nautilustrader.io/docs/latest/api_reference/>** — the upstream docs site has 17 module pages. Always check there for full type listings, edge-case behavior, and version-specific changes. This file is a curated map of the surface a strategy author actually touches.

Cross-checked against:
- Context7: `/nautechsystems/nautilus_trader` (5,940 snippets, High reputation)
- Auggie / Augment Code: `HyperFrequency/nautilus_trader` fork on the `develop` branch
- Live docs: <https://nautilustrader.io/docs/latest/>

---

## 1. Canonical Imports

What you import most often when writing a Nautilus strategy or harness:

| Layer | Symbol | Import |
| --- | --- | --- |
| Strategy | `Strategy` | `from nautilus_trader.trading.strategy import Strategy` |
| Strategy | `StrategyConfig` | `from nautilus_trader.config import StrategyConfig` |
| Backtest | `BacktestEngine` | `from nautilus_trader.backtest.engine import BacktestEngine` |
| Backtest | `BacktestEngineConfig` | `from nautilus_trader.config import BacktestEngineConfig` |
| Backtest (config-driven) | `BacktestNode` | `from nautilus_trader.backtest.node import BacktestNode` |
| Backtest config | `BacktestRunConfig`, `BacktestDataConfig`, `BacktestVenueConfig` | `from nautilus_trader.config import ...` |
| Live | `TradingNode` | `from nautilus_trader.live.node import TradingNode` |
| Live | `TradingNodeConfig` | `from nautilus_trader.config import TradingNodeConfig` |
| Logging | `LoggingConfig` | `from nautilus_trader.config import LoggingConfig` |
| IDs | `InstrumentId`, `Venue`, `TraderId`, `StrategyId`, `ClientId` | `from nautilus_trader.model.identifiers import ...` |
| Data | `Bar`, `BarType`, `BarSpecification`, `QuoteTick`, `TradeTick` | `from nautilus_trader.model.data import ...` |
| Enums | `AccountType`, `OmsType`, `OrderSide`, `TimeInForce`, `OrderType` | `from nautilus_trader.model.enums import ...` |
| Money/qty | `Money`, `Price`, `Quantity`, `Currency` | `from nautilus_trader.model.objects import ...` |
| Orders | `MarketOrder`, `LimitOrder`, `StopMarketOrder`, etc. | `from nautilus_trader.model.orders import ...` |
| Events | `OrderFilled`, `PositionOpened`, `PositionClosed` | `from nautilus_trader.model.events import ...` |

---

## 2. Strategy Lifecycle

A user strategy subclasses `Strategy` and overrides any subset of these handlers. Defaults log a warning and return; none are required.

```python
from decimal import Decimal
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.identifiers import InstrumentId


class MyStrategyConfig(StrategyConfig):
    instrument_id: InstrumentId   # "ETHUSDT-PERP.BINANCE"
    bar_type: BarType             # "ETHUSDT-PERP.BINANCE-15-MINUTE[LAST]-EXTERNAL"
    fast_ema_period: int = 10
    slow_ema_period: int = 20
    trade_size: Decimal
    order_id_tag: str


class MyStrategy(Strategy):
    def __init__(self, config: MyStrategyConfig) -> None:
        super().__init__(config)

    def on_start(self) -> None: ...
    def on_stop(self) -> None: ...
    def on_reset(self) -> None: ...
    def on_dispose(self) -> None: ...
```

### Handler reference

| Handler | When it fires | Override to … |
| --- | --- | --- |
| `on_start()` | Strategy started | Subscribe to data, request historical bars, set state |
| `on_stop()` | Strategy stopped | Cancel open orders, close positions, unsubscribe |
| `on_reset()` | Engine reset (e.g. between backtest runs) | Reset internal state |
| `on_dispose()` | Strategy disposed | Free external resources |
| `on_bar(bar: Bar)` | Bar received on a subscribed `BarType` | Trading logic |
| `on_quote_tick(tick: QuoteTick)` | Top-of-book update | Quote-driven logic |
| `on_trade_tick(tick: TradeTick)` | Trade print received | Trade-driven logic |
| `on_data(data: Data)` | Custom `Data` subtype received | Alt-data ingestion |
| `on_order_filled(event: OrderFilled)` | Fill received | Update position state, place follow-ons |
| `on_position_opened(event: PositionOpened)` | Position opened | Set stops/targets |
| `on_position_closed(event: PositionClosed)` | Position closed | Realize PnL, log |
| `on_event(event: Event)` | Any event | Catch-all if the typed handlers aren't enough |

System-only methods (do not call from user code): `handle_event`, `handle_bar`, `handle_quote_tick`, `handle_trade_tick` — these dispatch into the `on_*` handlers above.

---

## 3. BacktestEngine

Two ways to drive a backtest:

**(a) Direct programmatic** — for one-off scripts, notebooks, custom flows:

```python
from decimal import Decimal
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, LoggingConfig
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.objects import Money

engine = BacktestEngine(
    BacktestEngineConfig(
        trader_id=TraderId("BACKTESTER-001"),
        logging=LoggingConfig(log_level="INFO"),
    ),
)

SIM = Venue("SIM")
engine.add_venue(
    venue=SIM,
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    starting_balances=[Money(1_000_000, USD)],
)
engine.add_instrument(instrument)
engine.add_data(ticks)
engine.add_strategy(strategy)
engine.run()
result = engine.get_result()
engine.dispose()
```

**(b) Config-driven via `BacktestNode`** — for distributed / repeated runs:

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import BacktestRunConfig, BacktestDataConfig, BacktestVenueConfig

node = BacktestNode(configs=[BacktestRunConfig(...)])
results = node.run()
```

### `BacktestEngine` user-facing methods

| Method | Purpose |
| --- | --- |
| `add_venue(venue, oms_type, account_type, starting_balances, *, base_currency=None, default_leverage=Decimal("1"), leverages=None, margin_model=None, book_type=None, routing=None, modules=None, fill_model=None, fee_model=None, latency_model=None)` | Register a venue (must be added before its instruments) |
| `add_instrument(instrument)` | Register an instrument with its venue |
| `add_data(data, client_id=None, validate=True, sort=True)` | Bulk-add a `list[Data]` to the engine |
| `add_data_iterator(data_name, generator, client_id=None)` | Streaming low-level API: a generator that yields `list[Data]` chunks |
| `add_actor(actor)` / `add_actors(actors)` | Register a non-strategy `Actor` |
| `add_strategy(strategy)` / `add_strategies(strategies)` | Register `Strategy` instances |
| `add_exec_algorithm(algo)` / `add_exec_algorithms(algos)` | Register execution algorithms |
| `run(start=None, end=None)` | Run the configured backtest |
| `get_result() -> BacktestResult` | Get the result object after `run()` |
| `clear_data()` | Drop loaded data, keep state |
| `dispose()` | Drop everything; release resources |

---

## 4. TradingNode (Live)

```python
import asyncio
from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import TradingNodeConfig

node = TradingNode(TradingNodeConfig(...))
node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)
node.build()
try:
    node.run()                         # blocking, or:
    # asyncio.run(node.run_async())    # async
finally:
    node.dispose()
```

### `TradingNode` user-facing surface

| Property / method | Purpose |
| --- | --- |
| `trader_id`, `machine_id`, `instance_id` | Identity |
| `trader`, `cache`, `portfolio` | Read-only facades into the running system |
| `is_running()`, `is_built()` | State checks |
| `add_data_client_factory(name, factory)` | Wire a venue's market-data adapter (e.g. Hyperliquid, Binance) |
| `add_exec_client_factory(name, factory)` | Wire a venue's execution adapter |
| `add_stream_processor(callback)` | Attach a callback to the data stream |
| `build()` | Construct the internal clients from configured factories |
| `run()` / `async run_async()` | Start the node |
| `stop()` / `async stop_async()` | Graceful shutdown — checks Trader residual state, saves strategies if configured |
| `dispose()` | Tear down executor + event loop |
| `publish_bus_message(bus_msg)` | Inject a `BusMessage` into the internal message bus (not external) |

For Hyperliquid specifically, see `references/hyperliquid.md` and `references/hyperliquid_patch.py` (covers the SDK price-precision patch the HF fork applies).

---

## 5. Common Model Types

Quick mental model — what each type is for, where to import it from. Full attribute listings live in the upstream module pages linked at the bottom.

### Identifiers (`nautilus_trader.model.identifiers`)
- `Venue("SIM")`, `Venue("BINANCE")`
- `InstrumentId.from_str("ETHUSDT-PERP.BINANCE")`
- `TraderId("BACKTESTER-001")`
- `StrategyId("MyStrat-001")`
- `ClientId("BINANCE")`

### Data (`nautilus_trader.model.data`)
- `BarSpecification(step, BarAggregation.MINUTE, PriceType.LAST)`
- `BarType.from_str("ETHUSDT-PERP.BINANCE-15-MINUTE[LAST]-EXTERNAL")`
- `Bar`, `QuoteTick`, `TradeTick`

### Enums (`nautilus_trader.model.enums`)
- `OmsType.NETTING` | `OmsType.HEDGING`
- `AccountType.MARGIN` | `AccountType.CASH` | `AccountType.BETTING`
- `OrderSide.BUY` | `OrderSide.SELL`
- `TimeInForce.GTC` | `IOC` | `FOK` | `GTD` | `DAY`
- `OrderType.MARKET` | `LIMIT` | `STOP_MARKET` | `STOP_LIMIT` | `TRAILING_STOP_MARKET` …

### Quantitative objects (`nautilus_trader.model.objects`)
- `Money(1_000_000, USD)` — currency-aware amount
- `Price.from_str("100.25")`
- `Quantity.from_str("1.5")`
- `Currency.from_str("USD")`

### Orders (`nautilus_trader.model.orders`)
- `MarketOrder`, `LimitOrder`, `StopMarketOrder`, `StopLimitOrder`, `TrailingStopMarketOrder`, `TrailingStopLimitOrder`, `MarketIfTouchedOrder`, `LimitIfTouchedOrder`
- Order factories on the strategy: `self.order_factory.market(...)`, `.limit(...)`, etc.

### Events (`nautilus_trader.model.events`)
- Order lifecycle: `OrderSubmitted`, `OrderAccepted`, `OrderRejected`, `OrderCanceled`, `OrderExpired`, `OrderTriggered`, `OrderFilled`
- Position lifecycle: `PositionOpened`, `PositionChanged`, `PositionClosed`
- Account: `AccountState`

---

## 6. Upstream Module Index

When you need full type listings, go directly to the upstream page. These were the 17 pages the old dump concatenated:

| Page | Link |
| --- | --- |
| Backtest | <https://nautilustrader.io/docs/latest/api_reference/backtest> |
| Live | <https://nautilustrader.io/docs/latest/api_reference/live> |
| Trading | <https://nautilustrader.io/docs/latest/api_reference/trading> |
| Model — Data | <https://nautilustrader.io/docs/latest/api_reference/model/data> |
| Model — Events | <https://nautilustrader.io/docs/latest/api_reference/model/events> |
| Model — Identifiers | <https://nautilustrader.io/docs/latest/api_reference/model/identifiers> |
| Model — Instruments | <https://nautilustrader.io/docs/latest/api_reference/model/instruments> |
| Model — Objects | <https://nautilustrader.io/docs/latest/api_reference/model/objects> |
| Model — Orders | <https://nautilustrader.io/docs/latest/api_reference/model/orders> |
| Model — Position | <https://nautilustrader.io/docs/latest/api_reference/model/position> |
| Model — Tick scheme | <https://nautilustrader.io/docs/latest/api_reference/model/tick_scheme> |
| Common | <https://nautilustrader.io/docs/latest/api_reference/common> |
| Data | <https://nautilustrader.io/docs/latest/api_reference/data> |
| Execution | <https://nautilustrader.io/docs/latest/api_reference/execution> |
| Portfolio | <https://nautilustrader.io/docs/latest/api_reference/portfolio> |
| Risk | <https://nautilustrader.io/docs/latest/api_reference/risk> |
| Serialization | <https://nautilustrader.io/docs/latest/api_reference/serialization> |

---

## 7. HyperFrequency fork notes

The HF fork (`HyperFrequency/nautilus_trader`, branch `develop`) tracks upstream `nautechsystems/nautilus_trader` with one patched concern: **Hyperliquid price-precision handling**. See `references/hyperliquid_patch.py` and `references/hyperliquid-connector-full-guide.md` for the patch + adapter wiring. Behavior is otherwise upstream-equivalent.

---

## Notes on this file

- The previous `api.md` was a 469 KB / 13,684-line concatenation of all 17 upstream API pages. Replaced with this curated reference because exhaustive type dumps don't help — the live docs site is the source of truth.
- This file is for **navigation and recall**, not full reference. If you need exhaustive type info, follow the module link above.
- Last cross-checked: 2026-05-20 (Context7 `/nautechsystems/nautilus_trader`, Auggie on `HyperFrequency/nautilus_trader` `develop`, nautilustrader.io live docs).
