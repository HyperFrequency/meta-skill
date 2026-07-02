# Reference implementations

Minimal, dependency-light reference implementations for the core microstructure
estimators. These are teaching/validation references — for production use the
library implementations noted in `SKILL.md` (`mlfinlab`, `nautilus_trader`).

## Lee-Ready trade-sign classification

```python
import pandas as pd
import numpy as np


def lee_ready_classify(
    trades: pd.DataFrame,
    quotes: pd.DataFrame,
    quote_lag_ms: int = 0,
) -> pd.Series:
    """Classify trades as buyer-initiated (+1) or seller-initiated (-1).

    Args:
        trades: DataFrame with columns ['timestamp', 'price', 'size'], sorted by timestamp.
        quotes: DataFrame with columns ['timestamp', 'bid', 'ask'], sorted by timestamp.
        quote_lag_ms: Match each trade to the quote prevailing this many ms before it.
                      Lee & Ready (1991) used 5 seconds; modern data often uses 0.

    Returns:
        Series of {+1, -1} indexed like trades. NaN where no prevailing quote exists.

    Reference: Lee & Ready (1991), "Inferring Trade Direction from Intraday Data",
    Journal of Finance 46(2), 733-746.
    """
    trades = trades.copy().sort_values("timestamp").reset_index(drop=True)
    quotes = quotes.copy().sort_values("timestamp").reset_index(drop=True)

    # Build the lookup timestamp (trade time minus lag)
    lookup_ts = trades["timestamp"] - pd.Timedelta(milliseconds=quote_lag_ms)

    # merge_asof finds the most recent quote at-or-before each lookup timestamp
    matched = pd.merge_asof(
        pd.DataFrame({"timestamp": lookup_ts, "trade_idx": trades.index}),
        quotes,
        on="timestamp",
        direction="backward",
    )

    mid = (matched["bid"] + matched["ask"]) / 2.0
    price = trades["price"].values

    sign = np.where(price > mid, 1, np.where(price < mid, -1, 0))

    # Tick rule fallback for at-midpoint trades
    price_diff = np.diff(price, prepend=price[0])
    tick_sign = np.sign(price_diff)
    # Zero-tick: carry forward the previous non-zero sign
    for i in range(1, len(tick_sign)):
        if tick_sign[i] == 0:
            tick_sign[i] = tick_sign[i - 1]

    sign = np.where(sign == 0, tick_sign, sign)
    return pd.Series(sign, index=trades.index, name="trade_sign")
```

## Order Flow Imbalance (Cont-Kukanov-Stoikov)

```python
def order_flow_imbalance(book_events: pd.DataFrame) -> pd.Series:
    """Compute event-level OFI contributions at the top of the book.

    Args:
        book_events: DataFrame with columns ['timestamp', 'bid', 'bid_size', 'ask', 'ask_size'],
                     one row per book update.

    Returns:
        Series of per-event OFI contributions. Sum over a window for the windowed OFI.

    Reference: Cont, Kukanov, Stoikov (2014), "The Price Impact of Order Book Events",
    Journal of Financial Econometrics 12(1), 47-88. DOI: 10.1093/jjfinec/nbt003.
    """
    b = book_events
    prev_bid = b["bid"].shift(1)
    prev_ask = b["ask"].shift(1)
    prev_bid_size = b["bid_size"].shift(1)
    prev_ask_size = b["ask_size"].shift(1)

    # Bid-side flow
    e_bid = np.where(
        b["bid"] > prev_bid, b["bid_size"],
        np.where(b["bid"] == prev_bid, b["bid_size"] - prev_bid_size,
                 -prev_bid_size),
    )
    # Ask-side flow (sign-flipped: ask down or smaller is buying pressure)
    e_ask = np.where(
        b["ask"] < prev_ask, b["ask_size"],
        np.where(b["ask"] == prev_ask, b["ask_size"] - prev_ask_size,
                 -prev_ask_size),
    )

    ofi = pd.Series(e_bid - e_ask, index=b.index, name="ofi")
    return ofi.fillna(0)


# Windowed OFI for a feature column
# windowed_ofi = order_flow_imbalance(book).rolling("1s", on=book["timestamp"]).sum()
```

## VPIN

```python
def vpin(
    trades: pd.DataFrame,
    volume_per_bucket: float,
    window_buckets: int = 50,
) -> pd.Series:
    """Volume-synchronized PIN over rolling volume buckets.

    Args:
        trades: DataFrame with ['timestamp', 'price', 'size', 'sign'] (sign from Lee-Ready).
        volume_per_bucket: target volume per bucket (e.g. 1/50 of avg daily volume).
        window_buckets: number of buckets to average over (default 50).

    Returns:
        Series of VPIN values, one per completed volume bucket.

    Reference: Easley, López de Prado, O'Hara (2012), "Flow Toxicity and Liquidity
    in a High-Frequency World", Review of Financial Studies 25(5), 1457-1493.
    """
    # Cumulative volume and bucket index
    cum_vol = trades["size"].cumsum()
    bucket_idx = (cum_vol // volume_per_bucket).astype(int)

    # Aggregate buy and sell volume per bucket
    buy_vol = trades["size"] * (trades["sign"] == 1)
    sell_vol = trades["size"] * (trades["sign"] == -1)

    per_bucket = pd.DataFrame({
        "buy": buy_vol.groupby(bucket_idx).sum(),
        "sell": sell_vol.groupby(bucket_idx).sum(),
    })
    imbalance = (per_bucket["buy"] - per_bucket["sell"]).abs()

    return (imbalance.rolling(window_buckets).sum() /
            (window_buckets * volume_per_bucket)).rename("vpin")
```

## Kyle's lambda

```python
import statsmodels.api as sm


def kyle_lambda(returns: pd.Series, signed_volume: pd.Series) -> float:
    """OLS slope of returns on signed order flow. Higher = more price impact per unit flow.

    Reference: Kyle (1985), "Continuous Auctions and Insider Trading", Econometrica 53(6).
    """
    df = pd.concat([returns, signed_volume], axis=1).dropna()
    df.columns = ["ret", "sv"]
    X = sm.add_constant(df["sv"])
    model = sm.OLS(df["ret"], X).fit()
    return float(model.params["sv"])
```
