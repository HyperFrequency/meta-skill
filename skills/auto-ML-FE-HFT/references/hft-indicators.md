# Section C — HFT indicator catalogue

Each entry: intuition + ≤25-line code + when-to-use. Cross-link where the math has its own skill home.

## C.1 Realized volatility with bipower variation jump component

Realized variance = sum of squared intraday returns. **Bipower variation** (Barndorff-Nielsen & Shephard 2004) = sum of products of adjacent absolute returns — jump-robust. The gap `RV − BV` isolates the jump contribution. Use jump-detected vol when news events drive your asset.

```python
# Realized volatility + bipower variation jump detection.
import numpy as np
import pandas as pd

def realized_vol(returns: pd.Series, window: int) -> pd.DataFrame:
    rv = returns.pow(2).rolling(window).sum()
    bv = (returns.abs() * returns.abs().shift(1)).rolling(window).sum() * (np.pi / 2)
    jump = (rv - bv).clip(lower=0)
    return pd.DataFrame({
        "rv": rv,
        "bv": bv,
        "jump_component": jump,
        "rv_annualized": np.sqrt(rv * (252 * 1440 / window)),  # 1-min bars → annualised
    })

r = pd.read_parquet("returns_1m.parquet")["log_ret"]
features = pd.concat([
    realized_vol(r, w).add_suffix(f"_{w}m") for w in (5, 60, 1440)
], axis=1)
```

When to use: any model where conditional vol matters — direction, vol-of-vol carry, breakout detection. Pairs with `garch-volatility` for parametric forecasts.

## C.2 Order-flow toxicity (VPIN) — cross-link

VPIN (Easley-López de Prado-O'Hara 2012) = buy/sell volume imbalance in volume-time buckets. High VPIN → toxic flow → execution risk. **See `microstructure-analysis`.** Consume as a column; don't recompute here.

## C.3 Order-flow imbalance (OFI) — cross-link

OFI = signed sum of top-of-book quantity changes (Cont-Kukanov-Stoikov 2014). Sharp predictor of next-second mid-price moves. **See `microstructure-analysis`.**

## C.4 Effective / realized / quoted spread

**Quoted** = `ask − bid` at trade time. **Effective** = `2·|P_t − M_t|` (actual trade cost vs mid). **Realized** = `2·D_t·(P_t − M_{t+5min})` (cost net of permanent impact).

```python
# Quoted, effective, realized spread on a trades-with-quotes table.
import pandas as pd

q = pd.read_parquet("quotes.parquet")           # ts, bid, ask, mid
tr = pd.read_parquet("trades.parquet")          # ts, price, size, side (+1 buy / -1 sell)
tr = pd.merge_asof(tr.sort_values("ts"), q.sort_values("ts"), on="ts", direction="backward")

tr["quoted_spread"]   = tr["ask"] - tr["bid"]
tr["effective_spread"]= 2.0 * (tr["price"] - tr["mid"]).abs()

# Realized spread vs mid 5 minutes ahead.
future_mid = q.set_index("ts")["mid"].reindex(
    tr["ts"] + pd.Timedelta("5min"), method="nearest"
).values
tr["realized_spread"] = 2.0 * tr["side"] * (tr["price"] - future_mid)
```

When to use: execution cost models, market-making calibration, TCA on backtests.

## C.5 Trade-sign autocorrelation (Bouchaud et al.)

Trade signs are heavily autocorrelated at HFT scales — Bouchaud-Farmer-Lillo (2009) document power-law decay over hundreds of trades. Use lag-k autocorrelation as a feature; anomalously low → regime shift.

```python
# Trade-sign autocorrelation at multiple lags.
import pandas as pd

signs = pd.read_parquet("trades.parquet")["side"]  # ±1
acf = pd.Series({
    f"sign_acf_lag_{k}": signs.autocorr(lag=k) for k in (1, 5, 10, 50, 100, 500)
})
```

When to use: trade-flow continuation, market-impact models, regime detection.

## C.6 Roll's spread estimator

Roll (1984): `effective_spread ≈ 2·sqrt(−Cov(Δp_t, Δp_{t−1}))` when autocovariance is negative (bid-ask bounce). Cheap spread proxy from trade prices alone — use when quotes are missing.

```python
# Roll's implicit spread from trade-price autocovariance.
import numpy as np
import pandas as pd

def roll_spread(prices: pd.Series, window: int = 1000) -> pd.Series:
    dp = prices.diff()
    cov = dp.rolling(window).cov(dp.shift(1))
    return 2.0 * np.sqrt((-cov).clip(lower=0))

spread_proxy = roll_spread(pd.read_parquet("trades.parquet")["price"])
```

When to use: quote-poor venues, pre-2010 historical backtests.

## C.7 Amihud illiquidity ratio

Amihud (2002): `ILLIQ_t = |return_t| / dollar_volume_t`. Big return on low volume → illiquid. Strong cross-sectional risk factor, useful conditioning feature.

```python
# Amihud illiquidity at daily or intraday scale.
import pandas as pd

df = pd.read_parquet("ohlcv.parquet")
df["dollar_volume"] = df["close"] * df["volume"]
df["amihud_illiq"] = df["close"].pct_change().abs() / df["dollar_volume"].replace(0, pd.NA)
df["amihud_illiq_20"] = df["amihud_illiq"].rolling(20).mean()
```

When to use: cross-asset conditioning, TCA models, sizing constraints.

## C.8 Kyle's lambda — cross-link

Kyle (1985) `λ` is the slope of price impact per unit signed volume: `Δp_t ≈ λ · signed_volume_t`. Higher λ → less liquidity. **See `microstructure-analysis`.** Use rolling-windowed λ as a feature.

## C.9 Hasbrouck information share (multi-venue same asset)

Hasbrouck (1995) decomposes the variance of the common efficient price into per-venue contributions; the highest-share venue is the price leader. Non-trivial: VECM + Cholesky bounds — use `mlfinlab.microstructural_features` or hand-roll via statsmodels. **Recommendation:** do not roll Hasbrouck at HFT cadence; compute monthly on full panels and treat as a slow conditioning variable.

```python
# Sketch only — implementation requires VECM. See mlfinlab.microstructural_features.
# Expect ~100 lines or a library call.
```

## C.10 Hawkes self-exciting intensity — cross-link

Hawkes processes model self- and cross-excitation: a trade raises the probability of another nearby. Intensity `λ(t)` is itself a feature — high intensity → continued activity. **See [`microstructure-analyst`](../../microstructure-analyst/SKILL.md) §C.Hawkes for the implementation, and [`microstructure-feature-engineering`](../../microstructure-feature-engineering/SKILL.md) for the bar-aligned feature.** No standalone `hawkes-process` skill exists; Hawkes is owned by the two microstructure skills above.

## C.11 Realized skewness and kurtosis at intraday scale

Higher moments of intraday returns are predictive (Amaya-Christoffersen-Jacobs-Vasquez 2015 — realized skew predicts cross-sectional next-week returns). Cheap to compute, often missed.

```python
# Intraday realized skewness and kurtosis over rolling windows.
import pandas as pd

r = pd.read_parquet("returns_1m.parquet")["log_ret"]
rskew = r.pow(3).rolling(390).sum() / (r.pow(2).rolling(390).sum().pow(1.5))
rkurt = r.pow(4).rolling(390).sum() / (r.pow(2).rolling(390).sum().pow(2))
features = pd.DataFrame({"rskew_1d": rskew, "rkurt_1d": rkurt})
```

When to use: as conditioning features for tail-risk models, for cross-sectional ranking, alongside realized vol.
