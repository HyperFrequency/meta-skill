# Bar construction

The bar clock determines the meaning of every downstream statistic. Lopez de Prado AFML Ch. 2 argues for **information-driven bars** (tick, volume, dollar, imbalance) over time bars on the grounds that information arrival is uneven in clock time but more uniform in event time. The argument is empirical: returns sampled in volume time are closer to IID than returns sampled in clock time, which makes downstream statistical methods (i.i.d. assumptions, stationarity tests, even ADF) far more honest.

## Time bars

Default. Easy to align with macro features and exogenous calendars. Defects: heavy autocorrelation in intraday volatility, intraday seasonality eats your features alive, low-information periods (e.g. lunch lull) over-represented.

## Tick bars

Bar every N trades. Reduces intraday seasonality somewhat; still vulnerable to message-stuffing / spoofing inflating tick counts.

## Volume bars

Bar every N contracts/coins. Lopez de Prado's default recommendation when you can choose. Closer to IID returns.

```python
import numpy as np
import pandas as pd


def volume_bars(trades: pd.DataFrame, volume_per_bar: float) -> pd.DataFrame:
    """Build volume bars from a (ts_event, price, size) trades DataFrame.

    Each bar contains exactly `volume_per_bar` of cumulative size (the last
    trade in the bar is split conceptually; here we keep it whole and let
    the bar slightly overshoot — fine for ML features, not for accounting).
    """
    t = trades.sort_values("ts_event").reset_index(drop=True)
    cum = t["size"].cumsum()
    bar_id = (cum // volume_per_bar).astype(int)
    g = t.groupby(bar_id)
    out = pd.DataFrame({
        "ts_event": g["ts_event"].last(),
        "open":  g["price"].first(),
        "high":  g["price"].max(),
        "low":   g["price"].min(),
        "close": g["price"].last(),
        "volume": g["size"].sum(),
        "n_trades": g.size(),
    })
    return out.reset_index(drop=True)
```

## Dollar bars

Bar every $X of notional. Robust to splits, listings, price changes; recommended over volume bars when the asset's price level changes materially over the sample (e.g. multi-year crypto / equities).

```python
def dollar_bars(trades: pd.DataFrame, dollars_per_bar: float) -> pd.DataFrame:
    """Bar every `dollars_per_bar` of notional (price * size).

    Same shape as volume_bars; only the bar-id computation changes.
    """
    t = trades.sort_values("ts_event").reset_index(drop=True)
    notional = t["price"].to_numpy() * t["size"].to_numpy()
    cum = np.cumsum(notional)
    bar_id = (cum // dollars_per_bar).astype(int)
    g = t.groupby(bar_id)
    return pd.DataFrame({
        "ts_event": g["ts_event"].last(),
        "open": g["price"].first(),
        "high": g["price"].max(),
        "low":  g["price"].min(),
        "close": g["price"].last(),
        "dollars": pd.Series(notional, index=t.index).groupby(bar_id).sum(),
        "volume": g["size"].sum(),
        "n_trades": g.size(),
    }).reset_index(drop=True)
```

## Imbalance bars (tick / volume / dollar)

Bar when the running *signed* imbalance exceeds a threshold tied to its expected value (AFML Ch. 2.4). Captures *information events*: each bar contains roughly the same quantity of signed surprise. The threshold is dynamic — Lopez de Prado uses an exponentially-weighted estimate of `E[θ_T]` from prior bars.

```python
def tick_imbalance_bars(
    trades: pd.DataFrame,
    initial_threshold: float,
    ewma_alpha: float = 0.05,
) -> pd.DataFrame:
    """Tick imbalance bars (AFML Ch. 2.4). `trades` must have a signed `b`
    column in {-1, +1} (apply Lee-Ready first; see microstructure-analysis).
    Threshold adapts via EWMA of |θ_T| from prior bars.
    """
    t = trades.sort_values("ts_event").reset_index(drop=True)
    signs = t["b"].to_numpy()
    out, cum, start, threshold = [], 0.0, 0, float(initial_threshold)
    for i, s in enumerate(signs):
        cum += s
        if abs(cum) >= threshold:
            seg = t.iloc[start : i + 1]
            theta = abs(cum)
            out.append({"ts_event": seg["ts_event"].iloc[-1],
                        "open": seg["price"].iloc[0], "close": seg["price"].iloc[-1],
                        "high": seg["price"].max(), "low": seg["price"].min(),
                        "n_ticks": len(seg), "theta": theta})
            threshold = ewma_alpha * theta + (1 - ewma_alpha) * threshold
            cum, start = 0.0, i + 1
    return pd.DataFrame(out)
```

Volume-imbalance and dollar-imbalance variants follow the same shape with `signs * size` and `signs * size * price` respectively.
