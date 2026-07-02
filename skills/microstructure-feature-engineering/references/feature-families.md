# Microstructure-specific feature families

All snippets assume `import numpy as np` and `import pandas as pd`.

## Realized variance and bipower-variation jump decomposition

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

## Trade-sign autocorrelation (Bouchaud market-impact memory)

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

## Hawkes intensity and branching ratio

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

## Micro-price (Stoikov)

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

## HMM regime as a categorical feature

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

## Spread features (quoted, effective, realized)

Following Huang & Stoll 1997: **quoted spread** `s_q = ask - bid` is the cost of crossing now; **effective spread** `s_e = 2·ε·(P_trade - mid)` is what the taker actually paid; **realized spread** `s_r = 2·ε·(P_trade - mid_{t+Δ})` (typically Δ=5 min) is the maker's revenue after adverse selection. `s_e - s_r` is the price impact. As features, ratios `s_e/s_q` and `s_r/s_e` are stationarity-friendly proxies for liquidity quality and adverse-selection intensity respectively.

## Queue position (L3 only)

With MBO/L3 data you can reconstruct exact queue position by tracking individual order IDs (`nautilus_trader`'s `OrderBookDelta` does this). Queue position is an *execution* feature (conditions fill probability), not a directional signal — see `microstructure-analysis` for the realism argument.

## OFI feature stream aligned to bars

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

## Triple-barrier labeling at microstructure scale

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

## Aggregation join — assembling the feature matrix

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
