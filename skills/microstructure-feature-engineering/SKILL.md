---
name: microstructure-feature-engineering
description: Turn raw microstructure indicators (VPIN, OFI, book imbalance, trade signs) into ML-ready features. Covers information-driven bar construction (tick, volume, dollar, imbalance — Lopez de Prado AFML Ch. 2), microstructure noise filtering (two-time-scale RV, bipower variation jump decomposition), Hawkes intensity features, micro-price (Stoikov), HMM regime features, Bouchaud trade-sign autocorrelation, and leakage-safe assembly into a bar-aligned feature matrix. Triggers on phrases like "microstructure features", "OFI features", "volume bars", "dollar bars", "realized variance", "Hawkes features for trading", "L2 order-book features for ML", "tick-level feature engineering", "micro-price feature", "information-driven bars", "imbalance bars". For raw indicator computation use microstructure-analysis; for general feature engineering use feature-engineering; for regime fitting use markov-regime-detection; for purged CV use model-evaluation.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
license: HyperFrequency original (citations to external academic + library work)
---

# Microstructure Feature Engineering

This skill is the bridge between a stream of raw microstructure *indicators* (the OFI, VPIN, queue-position, trade-sign output of the sibling `microstructure-analysis` skill) and an ML-ready *feature matrix*. It is opinionated about bar construction, normalization, noise filtering, jump/continuous variance decomposition, regime augmentation, and the leakage discipline required when the sample frequency is ticks rather than days.

## When to use

Use this skill when:

- You have a stream of raw microstructure indicators (OFI, VPIN, book imbalance, signed trade flow) and need to turn them into rows of an ML feature matrix.
- You are deciding between time bars, tick bars, volume bars, dollar bars, or imbalance bars for sub-daily / intraday work.
- A short-horizon model trained on time bars is being killed by intra-day non-stationarity (volume seasonality, opening auction, lunch lull) and you suspect the bar clock is the problem.
- You need realized-variance features that separate continuous diffusion from jumps (BNS bipower).
- You are adding trade-clustering intensity (Hawkes) or hidden-state (HMM) features to a model.
- You are auditing a microstructure ML pipeline for look-ahead leakage at the *bar boundary* (the leakage modes here are different from those at daily-bar scale).

Do **not** use this for:

- Raw indicator math (OFI definition, Lee-Ready classification, VPIN formula) → `microstructure-analysis`.
- General feature pipelines for daily/weekly bars (technical indicators, daily fracdiff) → `feature-engineering`.
- The CV / out-of-sample design for the model that consumes these features → `model-evaluation`.

## Required tooling — the unified gateway contract

Route documentation lookup, AST parsing, and code-graph queries through the unified mcp2cli gateway (see the `neuro-harness` skill in this repo for the full endpoint table):

| Task | Use | Why |
| --- | --- | --- |
| Confirm current API for `mlfinlab`, `nautilus_trader`, `hmmlearn`, `statsmodels`, `tick` (Hawkes) | `docs-dual-lookup` skill (Context7 + Auggie in parallel) | These libraries have drifted APIs (mlfinlab went closed-source around 2022 — the OSS API of the last public v0.x is the reference here; flag the version explicitly). |
| Parse an existing feature-engineering script | `tree-sitter` skill via `mcp2cli tree-sitter parse` | Reliable function/decorator extraction beats grep. |
| Locate every caller of a feature transform across the repo | `mcp2cli gitnexus` or the `gitnexus-exploring` skill | Critical when renaming a feature column — the blast radius is large. |

**Do not** hand-roll an API call from training memory when wiring `mlfinlab.data_structures.standard_data_structures.get_dollar_bars` or `hmmlearn.hmm.GaussianHMM` — both have had breaking signature changes. Query the gateway first.

If `neuro-harness` is unreachable, say so and degrade to: Context7 → WebFetch on upstream docs → training-data recall as last resort, flagging the source of each claim.

## Pipeline relative to siblings

```
raw tape + L2/L3 deltas
        |
        v
+-------------------------+
| microstructure-analysis |  indicators (Lee-Ready, OFI, VPIN, queue,
|  -- units: events/ticks |  Kyle's lambda) at native event resolution
+-------------------------+
        |
        v
+----------------------------------+
| microstructure-feature-engineer. |  THIS SKILL: bars + noise filter +
|  -- units: ML feature ROWS       |  RV decomp + Hawkes + HMM-state +
|     one per bar, leakage-safe    |  fracdiff + leakage-safe assembly
+----------------------------------+
        |
        v
[ML / RL models]   [vectorbt / nautilus]   [model-evaluation: purged CV]
```

Contract: **indicators in, feature rows out** — every row is keyed by a single bar timestamp `ts_event` and uses only information observable at or before `ts_event`.

## Feature taxonomy

| Feature family | Input data layer | Aggregation scale | Stationarity | Expected predictive horizon | Decay |
|---|---|---|---|---|---|
| OFI integrated over bar | L1/L2 deltas | tick / volume / dollar | stationary at short horizons; drifts intraday | seconds → minutes | fast (seconds) |
| Static book imbalance, top-N | L2 snapshot | bar end | weakly stationary; depends on tick size | seconds → minutes | very fast |
| Trade-sign aggregates (Σ b_i, %buy_vol) | tape (signed via tick rule / Lee-Ready) | bar | stationary if symbol liquid | seconds → minutes | medium |
| Trade-sign autocorrelation (Bouchaud) | tape (signed) | over a window of N trades | stationary; long-memory by construction | minutes → hours (memory) | slow |
| Realized variance | tape, log-prices | bar | non-stationary in level, scale with vol regime | minutes → day | medium |
| RV jump component (BNS bipower) | tape, log-prices | bar | event-like, heavy-tail | minutes → day | medium |
| Two-time-scale RV (TSRV) | tape, ultra-HF prices | bar | as RV, with noise correction | minutes → day | medium |
| Hawkes intensity / branching ratio | tape (event times) | rolling window | non-stationary across regimes | seconds → minutes | fast |
| Micro-price (Stoikov) | L1 (bid, ask, sizes) | bar end snapshot | stationary in spread units | seconds | very fast |
| HMM decoded state | returns + RV (or returns alone) | bar | categorical; persistent | hours → days | slow |
| Queue position (own order) | L3 (MBO) | tick | not predictive on its own; conditions fill prob | n/a (execution feature) | n/a |
| Spread features (quoted, effective, realized) | L1 quotes + trades | bar | scale with vol regime | seconds → minutes | medium |
| VPIN | volume bars, signed flow | volume bar | regime indicator | minutes → hours | slow |

"Decay" is the rough timescale over which the feature loses informational value. Features with very fast decay are typically used as *state* features (consumed within the same bar) rather than as multi-bar lags.

## Bar construction

The bar clock determines the meaning of every downstream statistic. Lopez de Prado AFML Ch. 2 argues for **information-driven bars** (tick, volume, dollar, imbalance) over time bars on the grounds that information arrival is uneven in clock time but more uniform in event time. The argument is empirical: returns sampled in volume time are closer to IID than returns sampled in clock time, which makes downstream statistical methods (i.i.d. assumptions, stationarity tests, even ADF) far more honest.

### Time bars

Default. Easy to align with macro features and exogenous calendars. Defects: heavy autocorrelation in intraday volatility, intraday seasonality eats your features alive, low-information periods (e.g. lunch lull) over-represented.

### Tick bars

Bar every N trades. Reduces intraday seasonality somewhat; still vulnerable to message-stuffing / spoofing inflating tick counts.

### Volume bars

Bar every N contracts/coins. Lopez de Prado's default recommendation when you can choose. Closer to IID returns. Below: code for volume bars from a tape DataFrame.

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

### Dollar bars

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
        "dollars": (g["price"].apply(lambda s: s) * g["size"].apply(lambda s: s)).groupby(bar_id).sum()
            if False else pd.Series(notional, index=t.index).groupby(bar_id).sum(),
        "volume": g["size"].sum(),
        "n_trades": g.size(),
    }).reset_index(drop=True)
```

### Imbalance bars (tick / volume / dollar)

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

## Microstructure-specific feature families

### Realized variance and bipower-variation jump decomposition

The BNS bipower variation (Barndorff-Nielsen & Shephard 2004) separates total quadratic variation into a continuous diffusion part and a jump part. For intraday log-returns `r_i`, `i = 1..N`:

- `RV = Σ r_i^2` — total realized variance.
- `BV = (π/2) × Σ_{i=2..N} |r_i| × |r_{i-1}|` — bipower variation; estimates the *continuous* part.
- `J = max(RV - BV, 0)` — jump component.

The intuition: products of *consecutive* absolute returns swamp any single-bar jump, so `BV` is asymptotically jump-robust while `RV` is not. The difference is the jump.

```python
def rv_bipower(log_returns: pd.Series) -> dict:
    """Realized variance + BNS bipower jump decomposition (Barndorff-
    Nielsen & Shephard 2004). Pass log returns sampled at a fixed
    sub-bar grid (e.g. 1-second log-returns inside a 1-minute bar).
    """
    r = log_returns.dropna().to_numpy()
    if len(r) < 3:
        return {"RV": np.nan, "BV": np.nan, "J": np.nan}
    rv = np.sum(r ** 2)
    bv = (np.pi / 2.0) * np.sum(np.abs(r[1:]) * np.abs(r[:-1]))
    j = max(rv - bv, 0.0)
    return {"RV": float(rv), "BV": float(bv), "J": float(j)}
```

Pitfall: at very high frequencies (sub-second), `RV` is dominated by **microstructure noise** (bid-ask bounce, discreteness). The naive `RV` then diverges as you sample finer — the opposite of what theory says for a continuous semimartingale. Use **two-time-scale realized variance** (Zhang, Mykland, Aït-Sahalia 2005) to correct:

```python
def two_scale_rv(prices: pd.Series, K: int = 5) -> float:
    """Two-time-scale realized variance (TSRV) — Zhang, Mykland,
    Ait-Sahalia 2005, JASA. Robust to microstructure noise at HF.
    `prices` is a sub-bar series of mid-prices on a uniform grid.
    `K` is the slow-scale subsampling factor.
    """
    p = np.log(prices.dropna().to_numpy())
    n = len(p)
    if n < K + 2:
        return float("nan")
    # Fast-scale RV (all returns).
    rv_fast = float(np.sum(np.diff(p) ** 2))
    # Slow-scale RV averaged over K subsamples.
    rv_slow_subs = [float(np.sum(np.diff(p[k::K]) ** 2)) for k in range(K)]
    rv_slow = float(np.mean(rv_slow_subs))
    n_bar = (n - K + 1) / K
    return rv_slow - (n_bar / n) * rv_fast  # noise-bias corrected
```

### Trade-sign autocorrelation (Bouchaud market-impact memory)

Signed trade-flow exhibits long-memory autocorrelation — the Bouchaud-Gefen-Potters-Wyart 2004 paper documents a slowly-decaying power-law in `ρ(τ) = E[ε_t ε_{t+τ}]` where `ε_t` is the sign of trade t. This memory matters because impact aggregates over many trades, and ignoring it underestimates impact cost in execution backtests.

```python
def trade_sign_autocorr(signs: pd.Series, lags=(1, 5, 25, 100)) -> dict:
    """Bouchaud-style trade-sign autocorrelation at multiple lags.
    `signs` is a series of {-1, +1} from Lee-Ready or tick rule.
    Use lags spaced on a log grid because the decay is power-law,
    not exponential (Bouchaud et al. 2004).
    """
    s = signs.dropna().to_numpy().astype(float)
    out = {}
    s_centered = s - s.mean()
    var = float(np.dot(s_centered, s_centered) / len(s_centered))
    for k in lags:
        if len(s) <= k + 1:
            out[f"acf_lag{k}"] = float("nan")
            continue
        cov = float(np.dot(s_centered[:-k], s_centered[k:]) / (len(s) - k))
        out[f"acf_lag{k}"] = cov / var if var > 0 else float("nan")
    return out
```

Interpretation: typical equities and liquid crypto perps show `ρ(1) ≈ 0.2–0.5` and `ρ(τ) ~ τ^(-α)` with `α ≈ 0.5` (Bouchaud et al. 2004). Persistence is *not* arbitrage — it reflects metaorder splitting by execution algorithms. Use it as a feature, not as a directional signal.

### Hawkes intensity and branching ratio

A Hawkes process (Hawkes 1971) is a self-exciting point process: the conditional intensity of an event at time t depends on the history of prior events. For trade-arrival modeling, the canonical form is

`λ(t) = μ + Σ_{t_i < t} α × exp(-β (t - t_i))`

The **branching ratio** `n = α / β` measures how self-exciting the process is — `n → 1` means trades beget more trades (cascade regime), `n → 0` means trade arrivals are near-Poisson. Bacry, Mastromatteo & Muzy 2015 review Hawkes in finance and document branching ratios near 0.7–0.9 in liquid markets — markets are *strongly* self-exciting.

Two practical features:

- **Instantaneous intensity λ(t_bar_end)** — captures the "is the market in a frenzy right now" state.
- **Branching ratio estimated over a rolling window** — captures regime.

```python
from tick.hawkes import HawkesExpKern  # `pip install tick`


def fit_hawkes_branching(timestamps: np.ndarray, decay: float = 1.0) -> dict:
    """Fit a single-dim exp-kernel Hawkes to event times (seconds since
    epoch). Returns baseline μ, kernel norm α/β, and branching ratio.
    Use a rolling window in production; one-shot fit shown here.
    """
    learner = HawkesExpKern(decays=decay, max_iter=200)
    learner.fit([timestamps.astype(float).reshape(-1)])
    mu = float(learner.baseline[0])
    alpha = float(learner.adjacency[0, 0])  # already alpha/beta for normalized kernel in tick
    return {"mu": mu, "alpha_over_beta": alpha, "branching_ratio": alpha}
```

**Pitfall:** `tick` parameterizes the exponential kernel such that the fitted `adjacency` *is* the branching ratio (kernel integral). Other libraries (e.g. `hawkeslib`) return raw `α` and you must divide by `β` manually. Always confirm against the library's docstring — this is one of the easier silent-wrong-feature traps.

### Micro-price (Stoikov)

The **micro-price** (Stoikov 2018, *Quantitative Finance*) is a fair-value estimator that interpolates between mid and weighted-mid based on a learned/calibrated relationship between book imbalance and short-horizon return. The simple approximation often used in practice is the *weighted mid* (a first-order Stoikov):

`P_micro = (P_ask × Q_bid + P_bid × Q_ask) / (Q_bid + Q_ask)`

The full Stoikov micro-price uses a Markov-chain calibration to predict where the mid will be after the next "non-trivial" book update; the weighted-mid is its zeroth-order approximation but already a sharper fair-value than the mid for most liquid books.

```python
def weighted_mid(bid: float, ask: float, q_bid: float, q_ask: float) -> float:
    """Stoikov zeroth-order micro-price = weighted mid. Heavier book side
    pulls the fair value toward the *opposite* quote (more pressure to
    cross). At equal sizes it reduces to the mid."""
    denom = q_bid + q_ask
    if denom == 0:
        return 0.5 * (bid + ask)
    return (ask * q_bid + bid * q_ask) / denom
```

Pitfall: `weighted_mid` and `mid` are highly correlated, so including both as features adds little. Include only one (prefer `weighted_mid - mid` as a signed deviation feature) and feed the absolute level as a target-construction reference rather than as an input.

### HMM regime as a categorical feature

Cross-link: see `markov-regime-detection` for the full fitting workflow (model selection, initial conditions, instability, regime relabeling under permutation). Below is the minimum integration: fit a 3-state Gaussian HMM on log-returns and decode the most-likely state at each bar, then use that decoded state as a categorical (one-hot or label-encoded) feature.

```python
from hmmlearn.hmm import GaussianHMM


def hmm_state_feature(returns: pd.Series, n_states: int = 3, seed: int = 0) -> pd.Series:
    """Fit a Gaussian HMM on returns and decode the most-likely state.
    NOTE: This fits on the *full* series, which is a leakage hazard if
    used as a feature for predicting future returns. For production,
    fit on a rolling expanding window and decode only the next bar
    (see markov-regime-detection for the leakage-safe workflow).
    """
    r = returns.dropna().to_numpy().reshape(-1, 1)
    m = GaussianHMM(n_components=n_states, covariance_type="diag",
                    n_iter=200, random_state=seed)
    m.fit(r)
    states = m.predict(r)
    # Reorder by ascending mean return so state labels are stable across runs.
    order = np.argsort(m.means_.ravel())
    remap = {old: new for new, old in enumerate(order)}
    states = np.array([remap[s] for s in states])
    return pd.Series(states, index=returns.dropna().index, name="hmm_state")
```

### Spread features (quoted, effective, realized)

Following Huang & Stoll 1997: **quoted spread** `s_q = ask - bid` is the cost of crossing now; **effective spread** `s_e = 2·ε·(P_trade - mid)` is what the taker actually paid; **realized spread** `s_r = 2·ε·(P_trade - mid_{t+Δ})` (typically Δ=5 min) is the maker's revenue after adverse selection. `s_e - s_r` is the price impact. As features, ratios `s_e/s_q` and `s_r/s_e` are stationarity-friendly proxies for liquidity quality and adverse-selection intensity respectively.

### Queue position (L3 only)

With MBO/L3 data you can reconstruct exact queue position by tracking individual order IDs (`nautilus_trader`'s `OrderBookDelta` does this). Queue position is an *execution* feature (conditions fill probability), not a directional signal — see `microstructure-analysis` for the realism argument.

### OFI feature stream aligned to bars

The raw OFI is computed in `microstructure-analysis` (Cont-Kukanov-Stoikov 2014). Here we focus on the **alignment problem**: OFI is defined at the resolution of book updates, but the feature row is at the resolution of the chosen bar. Two correct strategies:

- **Bar-end integration.** Sum OFI from `ts_event_{i-1}` (exclusive) to `ts_event_i` (inclusive). Feature is the bar's total signed flow.
- **Bar-end snapshot.** Take OFI integrated over the last K seconds before `ts_event_i`. Decouples feature horizon from bar size.

The first is the default; the second is useful when you want the feature to have a constant decay regardless of bar duration (volume bars are not uniform in time).

```python
def ofi_bar_aligned(ofi_stream: pd.Series, bar_edges: pd.Series) -> pd.Series:
    """Sum OFI over each bar interval.

    ofi_stream: pd.Series indexed by ts_event (book-update granularity);
                values are signed OFI contributions per update.
    bar_edges:  pd.Series of bar end timestamps (e.g. volume-bar ts_event).

    Returns one OFI value per bar, indexed identically to bar_edges.
    """
    # cumulative OFI sampled at each bar edge, then differenced.
    cum = ofi_stream.cumsum()
    # `reindex` with method=ffill ensures every bar edge has the last
    # observed cumulative OFI — i.e. no look-ahead.
    aligned = cum.reindex(bar_edges.values, method="ffill")
    return aligned.diff().fillna(aligned.iloc[0]).set_axis(bar_edges.index)
```

The `method="ffill"` is load-bearing — it asserts "use the last cumulative OFI *as of or before* this bar edge." Using `method="bfill"` here is a textbook leakage bug.

### Triple-barrier labeling at microstructure scale

The triple-barrier method (Lopez de Prado AFML Ch. 3) generalizes naturally to microstructure. The key change is the *units of the barriers*: at daily scale you use σ-multiples of daily returns; at microstructure scale you use σ-multiples of *the right horizon's* returns (e.g. 30-tick or 1-minute realized vol).

```python
def triple_barrier_micro(
    prices: pd.Series,
    events: pd.Index,
    horizon_ticks: int = 30,
    pt_mult: float = 2.0,
    sl_mult: float = 1.0,
    vol_window: int = 200,
) -> pd.DataFrame:
    """Triple-barrier labels at tick / bar scale. For each event index,
    set upper barrier = +pt_mult * σ, lower = -sl_mult * σ, vertical
    = +horizon_ticks bars. σ is rolling stdev of returns over vol_window.
    Returns DataFrame with columns: t1 (vertical-barrier time), label.
    """
    p = prices.sort_index()
    ret = p.pct_change()
    sigma = ret.rolling(vol_window).std()
    rows = []
    for t0 in events:
        # locate t0 in the integer index of p so we can slice by tick count.
        i0 = p.index.get_loc(t0)
        i1 = min(i0 + horizon_ticks, len(p) - 1)
        s0 = sigma.iloc[i0]
        if not np.isfinite(s0) or s0 == 0:
            rows.append({"t0": t0, "t1": p.index[i1], "label": 0}); continue
        window_ret = p.iloc[i0 : i1 + 1] / p.iloc[i0] - 1.0
        up_hit = (window_ret >= pt_mult * s0).idxmax() if (window_ret >= pt_mult * s0).any() else None
        dn_hit = (window_ret <= -sl_mult * s0).idxmax() if (window_ret <= -sl_mult * s0).any() else None
        if up_hit is not None and (dn_hit is None or up_hit <= dn_hit):
            rows.append({"t0": t0, "t1": up_hit, "label": +1})
        elif dn_hit is not None:
            rows.append({"t0": t0, "t1": dn_hit, "label": -1})
        else:
            term_ret = window_ret.iloc[-1]
            rows.append({"t0": t0, "t1": p.index[i1], "label": int(np.sign(term_ret))})
    return pd.DataFrame(rows).set_index("t0")
```

This is intentionally lighter than the `feature-engineering` skill's macro version (which adds meta-labeling, sample-uniqueness weights, side-information). At microstructure scale, the `vol_window` parameter must be in *the same units as the bar* (ticks, volume bars, dollar bars) — mixing units here is a common bug.

### Aggregation join — assembling the feature matrix

The contract: one row per bar, indexed by `ts_event`, columns = features, **no value in row i depends on data observed after `ts_event_i`**.

```python
def assemble_feature_matrix(
    bars: pd.DataFrame,                 # one row per bar, indexed by ts_event
    ofi: pd.Series,                     # one OFI per bar (already aligned)
    micro: pd.Series,                   # weighted-mid at bar end
    sign_acf: pd.DataFrame,             # ACF features per bar
    rv: pd.DataFrame,                   # {RV, BV, J} per bar
    hmm_state: pd.Series,               # decoded state per bar
) -> pd.DataFrame:
    """Outer-join all features on the bars' ts_event index. Forward-fill
    is forbidden for any feature that uses future data (HMM, RV in some
    pipelines). Use `validate='one_to_one'` to catch alignment bugs.
    """
    X = bars[["close", "volume", "n_trades"]].copy()
    X = X.join(ofi.rename("ofi"),       how="left", validate="one_to_one")
    X = X.join(micro.rename("micro"),   how="left", validate="one_to_one")
    X = X.join(sign_acf,                how="left", validate="one_to_one")
    X = X.join(rv,                      how="left", validate="one_to_one")
    X = X.join(hmm_state,               how="left", validate="one_to_one")
    # Drop the warm-up region where any feature is NaN; never zero-fill.
    return X.dropna(how="any")
```

`validate='one_to_one'` is non-negotiable — silent many-to-one joins are a leading cause of phantom alpha in microstructure ML.

## Leakage + stationarity

The macro story (ADF / KPSS / fractional differencing for stationarity, purged-and-embargoed CV for leakage) is covered in detail by the sibling `feature-engineering` skill and the `model-evaluation` skill. Read those first. The microstructure-specific additions:

### Stationarity at the bar level

- **Volume / dollar / imbalance bars** make returns *much* closer to stationary than time bars. Run ADF on returns under each bar clock and pick the clock that produces the strongest rejection of the unit root. Lopez de Prado AFML Ch. 2.6 calls this out explicitly: the choice of bar clock is itself a stationarity intervention.
- **Fractional differencing** (`(1-L)^d` for non-integer `d`; AFML Ch. 5) is still worth it for *price-level* features (micro-price level, mid level) even after the bar clock is chosen well. Use `d` in `[0.3, 0.7]` for liquid intraday data; verify ADF passes at the chosen `d`.
- **Intraday seasonality** persists even under volume bars on instruments with strong session structure (open/close in equities, daily funding on perps). Subtract a rolling-window seasonal mean *computed without look-ahead* (use only past sessions' empirical seasonality) before fitting any model that assumes a stationary mean.

### Leakage modes specific to microstructure

| Mode | Where it bites | Fix |
|---|---|---|
| Bar-edge ffill direction | Aligning indicators to bars with `method='bfill'` instead of `'ffill'` | Always `'ffill'`. Treat `'bfill'` as a code smell in this skill. |
| HMM fit on full sample | Decoded state at time t depends on data from t+1..T | Roll-fit HMM on expanding window; decode only the latest state. |
| Triple-barrier overlap | Sample i's label depends on prices through `t1_i`, which overlaps sample j > i's *feature window*. Train/test partitions become non-IID. | Use purged + embargoed CV (`model-evaluation`); sample-uniqueness weights (AFML Ch. 4). |
| Volume-bar boundary look-ahead | The exact bar boundary depends on the trade that *crosses* the threshold; if you set features at `bar.close`, some features use info from a trade beyond the threshold | Set features at the *last trade with cumulative volume strictly less than the threshold*; alternatively, accept the small overshoot and document it. |
| Realized variance scale-mismatch | RV computed at sub-bar grid leaks into the bar's *own* return if you sample too finely | Choose sub-bar grid so that the bar's terminal return is computed only at the bar's last price, not at any intra-bar mid. |

### Cross-asset feature transfer

A feature trained on BTC-PERP at Binance does not, in general, transfer to ETH-PERP at Hyperliquid. The dimensions that break transfer:

- **Tick size** (book imbalance is scale-sensitive to it).
- **Tape granularity** (some venues coalesce; OFI computed on coalesced trades is biased low).
- **Maker rebates / funding cycle** (changes the optimal trade-sign autocorrelation regime).
- **Lit-vs-dark fraction** (irrelevant on most crypto venues, dominant on US equities).

When transferring, normalize features by venue-and-symbol *running statistics* (z-score against a 30-day rolling window of the same symbol-venue), and validate with a *within-symbol* CV before claiming cross-symbol generalization.

## End-to-end example

Goal: build a feature matrix for a short-horizon model on **BTC-USD perp**, Hyperliquid tape + L2, using 100-volume-coin bars, with OFI + micro-price + HMM-state + triple-barrier labels. Output stored as parquet.

```python
# 1) Load tape, quotes, OFI (see tardis-data-agent / nautilus for ingest;
#    OFI computed via microstructure-analysis).
trades = pd.read_parquet("trades_btc_hl.parquet")     # ts_event, price, size, b
quotes = pd.read_parquet("quotes_btc_hl.parquet")     # ts_event, bid, ask, q_bid, q_ask
ofi_stream = pd.read_parquet("ofi_btc_hl.parquet")["ofi"]

# 2) Volume bars at 100 BTC per bar.
bars = volume_bars(trades, volume_per_bar=100.0).set_index("ts_event")

# 3) Bar-aligned features.
ofi = ofi_bar_aligned(ofi_stream, bars.index.to_series())
q_at_bar = quotes.reindex(bars.index, method="ffill")
micro = pd.Series(
    [weighted_mid(b, a, qb, qa)
     for b, a, qb, qa in q_at_bar[["bid","ask","q_bid","q_ask"]].itertuples(index=False)],
    index=bars.index, name="micro",
)
log_ret = np.log(bars["close"]).diff()
rv  = pd.DataFrame([{"ts_event": ts, **rv_bipower(log_ret.loc[:ts].tail(10))}
                    for ts in bars.index]).set_index("ts_event")
acf = pd.DataFrame([{"ts_event": ts,
                     **trade_sign_autocorr(trades.loc[trades["ts_event"] <= ts].tail(500)["b"])}
                    for ts in bars.index]).set_index("ts_event")

# 4) HMM regime — for production, roll-fit on expanding window (see
#    markov-regime-detection); one-shot here is illustrative only.
hmm = hmm_state_feature(log_ret, n_states=3)

# 5) Assemble + label.
X = assemble_feature_matrix(bars, ofi, micro, acf, rv, hmm)
events = X.index[::5]
y = triple_barrier_micro(bars["close"], events, horizon_ticks=30,
                         pt_mult=2.0, sl_mult=1.0, vol_window=200)["label"]

# 6) Persist.
X.to_parquet("features_btc_hl_vol100.parquet")
y.to_parquet("labels_btc_hl_vol100.parquet")
```

Hand-off: `vectorbt` for the bar-level backtest of resulting signals; `nautilus-trader` for live/paper (re-implement the feature pipeline as a `Strategy` — do **not** ship the offline pandas pipeline to production unchanged); `model-evaluation` for purged + embargoed CV keyed on the triple-barrier `t1` column.

## Common pitfalls

- **Treating volume bars as if they were time bars.** Their timestamps are non-uniform; do not resample-to-frequency or align with exogenous time-bar features without explicit join logic. Bar duration is itself a feature.
- **Fitting HMM / VPIN / Hawkes once on the full sample and using the fitted parameters as features.** Each is a *training-leakage* sin. Roll-fit on expanding or sliding windows.
- **Mixing bar clocks within one feature matrix.** OFI on volume bars + RV on time bars + HMM trained on dollar-bar returns → the model is learning a clock, not a market.
- **Hawkes branching ratio confused with kernel norm.** Some libraries return `α`, others `α/β`. Confirm against docstrings; flag in the feature name (`branching_ratio` vs `alpha_raw`).
- **`weighted_mid` reported as `micro_price`.** Weighted-mid is the zeroth-order Stoikov approximation, not the full micro-price. Either implement the full Markov-chain calibration or rename the feature honestly.
- **Triple-barrier vol-window in the wrong units.** A 200 *tick* window inside a *volume bar* labeling routine is a unit error. Match the window to the bar clock.
- **Realized-variance jump component going negative.** Always clip `J = max(RV - BV, 0)` — finite-sample noise produces tiny negative jump components otherwise.
- **`join(..., validate='one_to_one')` removed "for speed".** This removes the only safeguard against silent many-to-one alignment. Keep it.

## Cross-links to other skills

- `microstructure-analysis` — raw indicators (OFI, VPIN, Lee-Ready, Kyle's lambda, queue position). This skill consumes them.
- `feature-engineering` — general ML features and labels, fractional differencing, meta-labeling, sample weights. This skill *specializes* it for microstructure data.
- `markov-regime-detection` — rigorous HMM fitting workflow (model selection, label-permutation, rolling estimation). Required if HMM-state is used as a feature.
- `model-evaluation` — purged + embargoed CV, deflated Sharpe, multiple-testing budget for the model that consumes these features.
- `nautilus-trader` — production execution layer; the source of L2/L3 in live and the right place to reimplement the feature pipeline as a strategy.
- `vectorbt` — bar-level backtest of the resulting signals.
- `tardis-data-agent` — historical tape + L2/L3 ingest (the most common data source for offline microstructure feature engineering).
- `ml-hypothesis-design` — microstructure features explode the trial space; deflate Sharpe accordingly.

## References

### Primary library
- `mlfinlab` (Hudson & Thames). Last fully-open-source version: `0.x` series (≈2021). Implements `data_structures` (tick/volume/dollar/imbalance bars), `labeling.triple_barrier`, `features.fracdiff`, `cross_validation.PurgedKFold`. Source: <https://github.com/hudson-and-thames/mlfinlab>. **Verified state:** the package moved to a closed-source / paid-tier model after the v0.x series; the OSS v0.x API is the reference here. Confirm current install path before pinning.

### Deep-dive docs
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. ISBN 978-1119482086. Chapters 2 (information-driven bars), 3 (triple-barrier labeling), 4 (sample uniqueness, sample weights), 5 (fractional differencing), 7 (purged + embargoed CV).
- `hmmlearn` user guide for `GaussianHMM`: <https://hmmlearn.readthedocs.io>. **Verify** `n_iter` / `covariance_type` defaults against the installed version.

### Adjacent libraries
- `tick` (Bacry et al.) — `HawkesExpKern`, `HawkesSumExpKern`. <https://github.com/X-DataInitiative/tick>. **Note:** `adjacency` in the `tick` exponential-kernel parameterization is already the branching-ratio (kernel integral). Other libraries (`hawkeslib`, `pyhawkes`) parameterize differently.
- `nautilus_trader` — L2/L3 ingest via `OrderBookDelta`; the canonical execution-side reimplementation target for any feature pipeline that needs to run live.
- `statsmodels` — ADF (`adfuller`), KPSS (`kpss`); standard stationarity tests.
- `vectorbt` / `vectorbt-pro` — bar-level backtest consumer; respects custom bar indexes if you persist them.

### Academic papers
- Barndorff-Nielsen, O. E., & Shephard, N. (2004). Power and Bipower Variation with Stochastic Volatility and Jumps. *Journal of Financial Econometrics*, 2(1), 1–37. DOI: 10.1093/jjfinec/nbh001.
- Andersen, T. G., Bollerslev, T., Diebold, F. X., & Labys, P. (2003). Modeling and Forecasting Realized Volatility. *Econometrica*, 71(2), 579–625. DOI: 10.1111/1468-0262.00418.
- Zhang, L., Mykland, P. A., & Aït-Sahalia, Y. (2005). A Tale of Two Time Scales: Determining Integrated Volatility With Noisy High-Frequency Data. *Journal of the American Statistical Association*, 100(472), 1394–1411. DOI: 10.1198/016214505000000169.
- Aït-Sahalia, Y., Mykland, P. A., & Zhang, L. (2005). How Often to Sample a Continuous-Time Process in the Presence of Market Microstructure Noise. *Review of Financial Studies*, 18(2), 351–416. DOI: 10.1093/rfs/hhi016.
- Hawkes, A. G. (1971). Spectra of some self-exciting and mutually exciting point processes. *Biometrika*, 58(1), 83–90. DOI: 10.1093/biomet/58.1.83.
- Bacry, E., Mastromatteo, I., & Muzy, J.-F. (2015). Hawkes Processes in Finance. *Market Microstructure and Liquidity*, 1(01), 1550005. DOI: 10.1142/S2382626615500057. arXiv: <https://arxiv.org/abs/1502.04592>.
- Bouchaud, J.-P., Gefen, Y., Potters, M., & Wyart, M. (2004). Fluctuations and Response in Financial Markets: The Subtle Nature of "Random" Price Changes. *Quantitative Finance*, 4(2), 176–190. DOI: 10.1080/14697680400000022. arXiv: <https://arxiv.org/abs/cond-mat/0307332>.
- Stoikov, S. (2018). The Micro-Price: A High-Frequency Estimator of Future Prices. *Quantitative Finance*, 18(12), 1959–1966. DOI: 10.1080/14697688.2018.1489139.
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The Price Impact of Order Book Events. *Journal of Financial Econometrics*, 12(1), 47–88. DOI: 10.1093/jjfinec/nbt003.
- Easley, D., López de Prado, M., & O'Hara, M. (2012). Flow Toxicity and Liquidity in a High-Frequency World. *Review of Financial Studies*, 25(5), 1457–1493.
- Huang, R. D., & Stoll, H. R. (1997). The Components of the Bid-Ask Spread: A General Approach. *Review of Financial Studies*, 10(4), 995–1034. DOI: 10.1093/rfs/10.4.995.
- Lee, C. M. C., & Ready, M. J. (1991). Inferring Trade Direction from Intraday Data. *Journal of Finance*, 46(2), 733–746.

### Tutorials
- Hudson & Thames blog + notebooks (open-source archive) — worked `mlfinlab` bars and triple-barrier examples. <https://hudsonthames.org>.

### Standard datasets
- **Databento** — MBO/MBP-10/MBP-1 for US equities, futures, options. Canonical L3 source.
- **Tardis.dev** — tape + L2/L3 for crypto (Binance, Hyperliquid, OKX, Bybit, …).
- **LOBSTER** — academic NASDAQ LOB reconstructions; standard in microstructure-noise benchmarks.

### Unverified / flagged
- `mlfinlab` API beyond v0.x is **not verified** here — Context7 only returned `requirements.txt`, and the package moved closed-source post-v0.x. Treat v0.x as the reference; query the installed version's docstrings before pinning specific function names.
- `tick`'s `HawkesExpKern.adjacency` semantics asserted above (branching-ratio for normalized exponential kernels) should be re-confirmed against the installed version — API churn between 0.6.x and 0.7.x.

**Last cross-checked:** 2026-05-20
