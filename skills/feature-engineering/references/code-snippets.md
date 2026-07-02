# Feature Engineering — Reference Code Snippets

Minimal reference implementations for the methods in `SKILL.md`. These are teaching-grade
implementations; `mlfinlab` provides the canonical, optimized versions (verify your installed
version's API before copying signatures).

## Triple-barrier labeling

```python
import numpy as np
import pandas as pd


def triple_barrier_labels(
    close: pd.Series,
    events: pd.DatetimeIndex,
    pt_sl: tuple[float, float],
    vol: pd.Series,
    vertical_barrier_bars: int,
) -> pd.DataFrame:
    """Label each event by which barrier is hit first.

    Args:
        close: Series of close prices indexed by timestamp.
        events: Event timestamps (e.g. from a CUSUM filter on returns).
        pt_sl: (profit_target_mult, stop_loss_mult) in units of vol.
               E.g. (2.0, 1.0) for +2σ profit / -1σ stop.
        vol: Series of per-bar volatility forecasts (e.g. EWMA of squared returns,
             aligned to event index).
        vertical_barrier_bars: Max bars before the vertical barrier fires.

    Returns:
        DataFrame indexed by event timestamp with columns:
          ['t1' (barrier-hit timestamp), 'ret' (return at exit), 'label' (-1, 0, +1)].

    Reference: López de Prado (2018), Advances in Financial Machine Learning, Ch. 3.
    """
    pt_mult, sl_mult = pt_sl
    out = pd.DataFrame(index=events, columns=["t1", "ret", "label"])

    # Pre-compute the vertical barrier timestamps
    close_idx = close.index
    for event_ts in events:
        i = close_idx.get_loc(event_ts)
        end_i = min(i + vertical_barrier_bars, len(close_idx) - 1)
        vert_ts = close_idx[end_i]

        # Path of prices from event to vertical barrier
        path = close.iloc[i:end_i + 1]
        entry_price = path.iloc[0]
        sigma = vol.loc[event_ts] if event_ts in vol.index else vol.asof(event_ts)

        if pd.isna(sigma) or sigma == 0:
            out.loc[event_ts] = [vert_ts, 0.0, 0]
            continue

        pt_price = entry_price * (1 + pt_mult * sigma)
        sl_price = entry_price * (1 - sl_mult * sigma)

        # First barrier hit
        hit_pt = path[path >= pt_price]
        hit_sl = path[path <= sl_price]

        ts_pt = hit_pt.index[0] if len(hit_pt) > 0 else None
        ts_sl = hit_sl.index[0] if len(hit_sl) > 0 else None

        candidates = [(ts, lbl) for ts, lbl in
                      [(ts_pt, 1), (ts_sl, -1), (vert_ts, 0)] if ts is not None]
        # Earliest barrier wins
        t1, label = min(candidates, key=lambda x: x[0])

        exit_price = close.loc[t1]
        ret = exit_price / entry_price - 1
        out.loc[event_ts] = [t1, ret, label]

    return out.astype({"ret": float, "label": int})
```

## Fractional differencing (López de Prado)

```python
def frac_diff_weights(d: float, threshold: float = 1e-4) -> np.ndarray:
    """Weights for fractional differencing, truncated when |w| < threshold."""
    weights = [1.0]
    k = 1
    while True:
        w = -weights[-1] * (d - k + 1) / k
        if abs(w) < threshold:
            break
        weights.append(w)
        k += 1
    return np.array(weights[::-1])  # most recent observation gets weight 1


def fractional_difference(series: pd.Series, d: float, threshold: float = 1e-4) -> pd.Series:
    """Apply fractional differencing (1-L)^d with truncated weights.

    Reference: López de Prado (2018), Advances in Financial Machine Learning, Ch. 5.
    """
    w = frac_diff_weights(d, threshold)
    width = len(w)
    out = pd.Series(index=series.index, dtype=float)
    for i in range(width - 1, len(series)):
        window = series.iloc[i - width + 1 : i + 1].values
        if np.isnan(window).any():
            continue
        out.iloc[i] = float(np.dot(w, window))
    return out
```

## Leakage-safe feature assembly

```python
from ta import add_all_ta_features
from ta.utils import dropna


def build_feature_matrix(
    ohlcv: pd.DataFrame,
    lookback_windows: list[int] = [5, 20, 60],
) -> pd.DataFrame:
    """Assemble a leakage-safe feature matrix from OHLCV bars.

    All rolling operations are right-aligned (one-sided); no .shift(-N) anywhere.
    """
    df = dropna(ohlcv.copy())
    log_ret = np.log(df["close"] / df["close"].shift(1))

    feats = pd.DataFrame(index=df.index)

    for w in lookback_windows:
        feats[f"ret_mean_{w}"] = log_ret.rolling(w).mean()
        feats[f"ret_std_{w}"]  = log_ret.rolling(w).std()
        feats[f"ret_skew_{w}"] = log_ret.rolling(w).skew()
        feats[f"rv_{w}"]       = (log_ret ** 2).rolling(w).sum()

    # Technical indicators from the `ta` library (pandas-native)
    df = add_all_ta_features(
        df, open="open", high="high", low="low", close="close", volume="volume",
        fillna=False,  # do NOT zero-fill; drop NaN warm-up rows downstream
    )
    indicator_cols = [c for c in df.columns if c not in ohlcv.columns]
    feats = pd.concat([feats, df[indicator_cols]], axis=1)

    # Critical: never assign a feature whose construction touches a future row.
    # If you must compute a feature that uses time-t+1 inside a helper, .shift(1) the result.
    return feats.dropna()  # drop the warm-up window
```

## Sample-weight uniqueness for overlapping labels

```python
def label_uniqueness(t1: pd.Series) -> pd.Series:
    """Average uniqueness weight for each labeled event with end-time t1.

    Args:
        t1: Series indexed by event start time; values are barrier-hit timestamps.

    Returns:
        Series of weights in (0, 1] for each event. Pass as sample_weight to the classifier.

    Reference: López de Prado (2018), Advances in Financial Machine Learning, Ch. 4.
    """
    # Concurrency: number of active labels at each bar
    bar_index = pd.date_range(t1.index.min(), t1.max(), freq=t1.index.freq or "T")
    concurrency = pd.Series(0, index=bar_index)
    for start, end in t1.items():
        concurrency.loc[start:end] += 1

    # Each event's weight = mean of 1/concurrency over its life
    weights = pd.Series(index=t1.index, dtype=float)
    for start, end in t1.items():
        weights.loc[start] = (1.0 / concurrency.loc[start:end]).mean()
    return weights
```
