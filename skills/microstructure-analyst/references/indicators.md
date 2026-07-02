# Microstructure indicators

Section C of the toolkit. For each indicator: a 1-paragraph intuition, the
math, a working Python kernel (≤ 30 lines, real imports), an interpretation
guide, and 2–3 common pitfalls. Where the math is more thoroughly motivated in
the sibling `microstructure-analysis` skill, cross-link rather than duplicate.

---

## VPIN (Volume-Synchronized Probability of Informed Trading)

**Intuition.** VPIN is a real-time estimator of order-flow *toxicity*: how
one-sided recent flow has been. The key trick is to clock by *volume*, not
time, because under heavy informed trading the volume clock and the
information clock are approximately the same — equal-volume buckets give a
stable estimator regardless of whether the trader is fast or slow.

**Math.** Bucket trades into equal-volume bars of size `V` each. For each
bucket compute buy volume `V_B` and sell volume `V_S` (with `V_B + V_S = V`).
Over a rolling window of `n` buckets:

```
VPIN = (1 / (n × V)) × Σ_{i=1..n} |V_B_i - V_S_i|
```

VPIN is bounded in [0, 1]; persistent values > 0.4 are large in equities and
have historically preceded liquidity withdrawal events (Easley, López de Prado,
O'Hara 2012). The BVC variant replaces tick-rule classification of `V_B / V_S`
inside each volume bar with the BVC estimator from
ingestion-and-reconstruction.md A.4.

**Implementation:**

```python
def vpin(trades: pd.DataFrame, volume_per_bucket: float,
         window_buckets: int = 50) -> pd.Series:
    """VPIN over rolling volume buckets.

    trades: ['ts', 'price', 'size', 'sign'] — sign from Lee-Ready or BVC.
    volume_per_bucket: target V per bucket, e.g. 1/50 of avg daily volume.
    window_buckets: n, default 50.

    Reference: Easley, López de Prado, O'Hara (2012), RFS 25(5), 1457-1493.
    """
    cum_vol = trades["size"].cumsum()
    bucket = (cum_vol // volume_per_bucket).astype(int)
    buy = (trades["size"] * (trades["sign"] == 1)).groupby(bucket).sum()
    sell = (trades["size"] * (trades["sign"] == -1)).groupby(bucket).sum()
    imbalance = (buy - sell).abs()
    return (imbalance.rolling(window_buckets).sum() /
            (window_buckets * volume_per_bucket)).rename("vpin")
```

**Interpretation.** Treat VPIN as a *regime* / *toxicity* indicator, not as
directional alpha. Use it to throttle execution (widen quotes, reduce size,
or step out) when persistently elevated; do not use it to predict the sign
of the next return.

**Pitfalls.**
- Time-bucketing instead of volume-bucketing. The "VPIN" you get from time
  buckets is a different, much weaker statistic.
- Look-ahead bias when the last partial bucket spills into the next: only
  emit VPIN for *complete* buckets.
- Mis-tuned `volume_per_bucket`. The canonical choice is ~1/50 of recent
  average daily volume; on illiquid instruments where ADV is unstable, use a
  rolling-trailing ADV rather than a fixed constant.

## NVWAP / VWAP family

**Intuition.** VWAP (Volume-Weighted Average Price) is the price you'd have
paid if you executed proportionally to total market volume. NVWAP normalises
VWAP into a comparable feature across instruments. TWAP ignores volume and
weights only by time — useful as a benchmark for execution-quality measurement,
not as an indicator.

**Math.** Over a window `W`:

```
VWAP   = Σ (price_i × size_i) / Σ size_i        # i ∈ W
TWAP   = (1/|W|) × Σ price_i
NVWAP  = (price - VWAP) / σ_price               # standardised deviation from VWAP
```

Anchored VWAP fixes the start of the window at a specific event (session open,
news print, swing high/low) and runs cumulatively from there.

**Implementation:**

```python
def vwap(prices: pd.Series, sizes: pd.Series,
         window: str = "1h") -> pd.Series:
    """Rolling time-window VWAP. Requires DatetimeIndex on `prices` and `sizes`.

    For anchored VWAP, pass `window=None` and use cumsum() instead of rolling.
    """
    pv = (prices * sizes).rolling(window).sum()
    v = sizes.rolling(window).sum()
    return (pv / v).rename("vwap")


def nvwap(prices: pd.Series, sizes: pd.Series,
          window: str = "1h", std_window: str = "1d") -> pd.Series:
    """Normalised VWAP deviation = (price - VWAP) / rolling stdev of price."""
    vw = vwap(prices, sizes, window)
    sigma = prices.rolling(std_window).std()
    return ((prices - vw) / sigma).rename("nvwap")
```

**Interpretation.** Positive NVWAP means price is trading above its
volume-weighted recent average — possible mean-reversion or trend-following
setup depending on the cross-sectional context. Anchored VWAP is heavily used
in discretionary day-trading as a level reference; treat any backtest of an
"anchored VWAP touch" strategy with extra skepticism around how the anchor
was chosen.

**Pitfalls.**
- Bar-VWAP vs tick-VWAP. Bar-aggregated VWAP loses sub-bar volume distribution
  information. For HFT signals, compute on ticks.
- Survivorship in anchor selection. Cherry-picking "the VWAP from the swing
  low" introduces look-ahead.

## Order-book imbalance (top-of-book, weighted, micro-price)

**Intuition.** When the bid is much bigger than the ask, marginal buyers will
have to walk the book further than marginal sellers — short-horizon price
drift biases up. The simplest version is the size ratio at the top of book.

**Math.**

```
I_top      = (bid_size - ask_size) / (bid_size + ask_size)         # ∈ [-1, +1]
I_weighted = Σ_k w_k (bid_size_k - ask_size_k) / Σ_k w_k (bid_size_k + ask_size_k)
             # with w_k a depth weight, e.g. 1 / (1 + |distance from mid|)
micro_price = (ask_size × bid + bid_size × ask) / (bid_size + ask_size)
             # Stoikov (2018) — sizes weight the *opposite* side's price
```

The Stoikov (2018) micro-price is *not* simply the size-weighted midpoint —
note the cross-weighting: the **ask** size weights the **bid** price, and
vice versa. Intuition: the side with more size is harder to lift, so the
fair price sits closer to the side with *less* size.

**Implementation:**

```python
def top_imbalance(bid_size, ask_size):
    return (bid_size - ask_size) / (bid_size + ask_size + 1e-12)

def weighted_imbalance(bid_sizes, ask_sizes, levels: int = 5,
                       decay: float = 0.5):
    """bid_sizes, ask_sizes: array-like of size at level 0..N-1.
    Decay weights deeper levels less."""
    w = np.exp(-decay * np.arange(levels))
    nb = np.dot(w, bid_sizes[:levels])
    na = np.dot(w, ask_sizes[:levels])
    return (nb - na) / (nb + na + 1e-12)

def stoikov_micro_price(bid, ask, bid_size, ask_size):
    """Stoikov (2018), Quantitative Finance 18(12), 1959-1966.
    Note the cross-weighting: ask SIZE * BID + bid SIZE * ASK."""
    denom = bid_size + ask_size
    return (ask_size * bid + bid_size * ask) / denom

def book_pressure(bid_sizes, ask_sizes, levels: int = 10):
    """Simple cumulative-depth imbalance over top N levels."""
    nb = np.sum(bid_sizes[:levels]); na = np.sum(ask_sizes[:levels])
    return (nb - na) / (nb + na + 1e-12)
```

**Interpretation.** `I_top` ∈ (+0.4, +1] is heavily bid-leaning; expect mean
reversion of recent down-moves and continuation of recent up-moves on the
seconds horizon. The micro-price is widely used as the *fair price reference*
for market-making quote placement — quote half-spread above and below it
rather than above and below the mid.

**Pitfalls.**
- Top-of-book only is brittle. A large `I_top` can flip on a single
  cancellation. Use `I_weighted` or `book_pressure` for stable signals.
- Don't conflate snapshot imbalance with OFI (flow). They have different
  signs in regimes like queue build-up (large positive `I_top`, low OFI).

## OFI — Order Flow Imbalance (Cont-Kukanov-Stoikov 2014)

**Intuition.** OFI measures the *net change* in liquidity at the top of the
book over a window — limit-order arrivals on the bid increase OFI, cancels on
the bid decrease it, and the ask side contributes with opposite sign. Unlike
static imbalance, OFI is event-flow-based, and the Cont-Kukanov-Stoikov (2014)
paper shows an approximately linear relationship between windowed OFI and
contemporaneous short-horizon returns.

**Math.** For each event with previous and current `(bid, bid_size, ask, ask_size)`:

```
e_n = +bid_size_n              if bid_n > bid_{n-1}
    = bid_size_n - bid_size_{n-1}   if bid_n = bid_{n-1}
    = -bid_size_{n-1}          if bid_n < bid_{n-1}

f_n = -ask_size_n              if ask_n > ask_{n-1}
    = ask_size_n - ask_size_{n-1}   if ask_n = ask_{n-1}
    = +ask_size_{n-1}          if ask_n < ask_{n-1}

OFI contribution_n = e_n + f_n
```

**Implementation:**

```python
def ofi(book_events: pd.DataFrame) -> pd.Series:
    """Per-event OFI contributions at top of book.

    book_events: ['ts', 'bid', 'bid_size', 'ask', 'ask_size'], one row per
    book update.  Sum over a window for the windowed OFI feature.

    Reference: Cont, Kukanov, Stoikov (2014), J. Financial Econometrics 12(1),
    47-88. arXiv:1011.6402.
    """
    b = book_events
    pb, pa = b["bid"].shift(1), b["ask"].shift(1)
    pbs, pas = b["bid_size"].shift(1), b["ask_size"].shift(1)
    e = np.where(b["bid"] > pb, b["bid_size"],
        np.where(b["bid"] == pb, b["bid_size"] - pbs, -pbs))
    f = np.where(b["ask"] > pa, -b["ask_size"],
        np.where(b["ask"] == pa, -(b["ask_size"] - pas), pas))
    return pd.Series(e + f, index=b.index, name="ofi").fillna(0.0)
```

**Interpretation.** Cont-Kukanov-Stoikov regress 10-second returns on summed
OFI over the same window and obtain `R² ≈ 0.65` for large-cap NYSE stocks.
The slope is the *impact coefficient* — useful as a per-instrument liquidity
parameter for execution-cost models.

**Pitfalls.**
- Sign error on the ask side. The CKS sign convention is that ask flow
  contributes with the *opposite* sign of bid flow because ask increases are
  bearish pressure, not bullish. Easy to flip by accident.
- Aggregating over wall-clock windows on event-time data. Sum OFI in
  *event-count* or *trade-volume* buckets if you want stable regressions.

## Spoofing / layering / quote-stuffing detection

**Intuition.** Spoofing is placing a large order with no intent to fill, to
move the price for a passive position on the opposite side. Layering is the
multi-level variant. Quote stuffing is a flood of cancel-replace at extreme
rates intended to slow competitors' market-data parsing or trigger their
adverse-selection signals. None of these patterns has a single canonical
academic detector — published work (Lee, Eom, Park 2013; Tao et al. 2020)
focuses on ex-post forensic detection on regulator-style L3 data with account
IDs. In the public-data setting, detection is **heuristic** — be honest about
that.

**Heuristics (paper-grounded):**

1. **Large-quote-then-cancel (LdP/Easley-style "submission/cancellation
   ratio"; Lee-Eom-Park 2013):** for each price level, track
   `cancel_size_t / posted_size_t` over a rolling 1-minute window. A level
   where >90% of recently posted size is cancelled within < 200 ms is a
   spoofing-pattern candidate.
2. **Layering signature (Lee-Eom-Park 2013):** ≥ 3 levels on the same side
   posted near-simultaneously and cancelled near-simultaneously (clustering of
   post-times and cancel-times within < 50 ms windows).
3. **Quote-stuffing TPS spike:** TPS (transactions per second, counting
   *messages* including cancels) > 99.9th-percentile of trailing 1-hour
   distribution, with cancel/post ratio > 0.95 in the same window.

**Implementation (operational, not exhaustive):**

```python
def cancel_post_ratio(book_events: pd.DataFrame, level_price: float,
                      window: str = "1min") -> pd.Series:
    """For one price level: rolling cancel-vs-post ratio.

    book_events: ['ts','price','size_delta','action'] with action in
    {'POST','CANCEL','EXECUTE'}.  size_delta is the signed quantity change.
    """
    at_level = book_events[book_events["price"] == level_price].set_index("ts")
    posts = (at_level["action"] == "POST").rolling(window).sum()
    cancels = (at_level["action"] == "CANCEL").rolling(window).sum()
    return (cancels / (posts + 1e-9)).rename("cancel_post_ratio")


def layering_candidates(book_events: pd.DataFrame, side: str,
                        min_levels: int = 3, cluster_ms: int = 50):
    """Find candidate layering episodes: ≥ min_levels POSTs on `side` within
    cluster_ms, followed by ≥ min_levels CANCELs on `side` within cluster_ms,
    with the cancel cluster preceding any aggressive trade on the OPPOSITE side.
    Returns DataFrame of (cluster_post_ts, cluster_cancel_ts, levels).
    """
    same = book_events[book_events["side"] == side].copy()
    same["bin"] = (same["ts"].astype("int64") // (cluster_ms * 1_000_000))
    posts = same[same["action"] == "POST"].groupby("bin").size()
    cancels = same[same["action"] == "CANCEL"].groupby("bin").size()
    cands = []
    for post_bin, n_post in posts[posts >= min_levels].items():
        # look for matching cancel cluster within ~10 bins (heuristic)
        for cancel_bin in range(post_bin + 1, post_bin + 11):
            if cancels.get(cancel_bin, 0) >= min_levels:
                cands.append({"post_bin": post_bin, "cancel_bin": cancel_bin,
                              "n_post": n_post, "n_cancel": cancels[cancel_bin]})
                break
    return pd.DataFrame(cands)
```

**Confidence levels for the patterns above:**

- *Large-quote-then-cancel ratio:* paper-grounded in Lee, Eom, Park (2013),
  J. Financial Markets 16, 227–252. **Medium confidence** — the paper uses
  the exact statistic on KRX data with known accounts. The exact thresholds
  (90% / 200 ms) are folklore practitioner heuristics.
- *Layering cluster:* paper-grounded in Lee, Eom, Park (2013); also discussed
  in Tao, Day, Ling, Drapeau (2020) "On Detecting Spoofing Strategies in High
  Frequency Trading" (arXiv:2009.14818). **Low–medium confidence** — public
  detectors must reconstruct order IDs heuristically because public L2 feeds
  don't carry them.
- *Quote-stuffing TPS spike:* folklore + regulator anecdote (CFTC reports
  post-Flash-Crash). **Low confidence** as a robust detector — high TPS also
  occurs in benign liquidity events (news prints, exchange resync).

**Pitfalls.**
- False positives during news events — TPS and cancel-post ratios both spike
  legitimately. Always combine with a news-event filter.
- L2 aggregation hides the per-order story; layering on a venue with hidden
  orders is undetectable from public feed alone.
- Treating spoofing detection as an alpha signal. It's a *throttle* / *risk*
  signal — when it fires, reduce passive size or step out of the market, not
  the other way around.

## Transactions-per-second (TPS) regime detection

**Intuition.** TPS — message rate per unit time — encodes the venue's
"temperature". Burst regimes are systematically different from steady-state:
during bursts, top-of-book has shorter expected lifetime, latency to the
exchange matters more, and adverse selection on resting orders is higher.

**Math.** EWMA-smoothed TPS with regime detection on quantile thresholds:

```python
def tps_regime(events: pd.DataFrame, halflife_sec: float = 5.0,
               q_burst: float = 0.99, q_quiet: float = 0.10,
               quantile_window: str = "1h") -> pd.DataFrame:
    """EWMA TPS plus quantile-band regime label.

    events: ['ts'] with one row per event (trade or book update).
    Returns DataFrame ['tps','regime'] with regime ∈ {'quiet','normal','burst'}.
    """
    s = events.set_index("ts").assign(one=1)["one"]
    # bucket to 1s for stable EWMA; halflife in seconds
    per_sec = s.resample("1s").sum()
    tps = per_sec.ewm(halflife=halflife_sec, times=per_sec.index,
                      adjust=False).mean()
    burst = tps.rolling(quantile_window).quantile(q_burst)
    quiet = tps.rolling(quantile_window).quantile(q_quiet)
    regime = pd.Series("normal", index=tps.index)
    regime[tps >= burst] = "burst"
    regime[tps <= quiet] = "quiet"
    return pd.DataFrame({"tps": tps, "regime": regime})
```

**Interpretation.** In burst regimes, widen passive quotes (or step out), and
treat any signal that depends on book-state stability with more skepticism.
The correlation between TPS spikes and same-window absolute returns is the
basic input to a "volatility-of-flow" regime indicator.

**Pitfalls.**
- Aggregating across instruments dilutes the signal. Compute per-instrument.
- Mixing trade-TPS and quote-TPS without separating. Quote-TPS during quiet
  trading is normal market-maker churn; trade-TPS bursts are different.

## Order-book spread dynamics

**Intuition.** The spread is the round-trip cost of immediacy. Its
distribution, decay after a sweep, and dependence on volatility are core
inputs to any execution model and to market-making profitability calculations.

**Definitions.**

```
quoted_spread     = ask - bid
half_spread       = (ask - bid) / 2
effective_spread  = 2 × sign × (trade_price - mid_at_trade)    # per trade
realized_spread   = 2 × sign × (trade_price - mid_at_trade_plus_5min)
                                                                # decay window
roll_spread       = 2 × sqrt(-Cov(Δp_t, Δp_{t-1}))           # Roll (1984)
                                                                # quote-free estimator
```

`effective_spread` measures what the aggressor *actually paid*; the difference
to `quoted_spread` is the contribution of price improvement. `realized_spread`
measures what the *liquidity provider earned*, net of adverse selection, over
a decay window (Hasbrouck and Schwartz often use 5 minutes; for crypto HFT
30 seconds is more realistic). Roll's (1984) spread estimator backs out an
implied spread from autocovariance of price changes — useful when you only
have trades, no quotes.

**Implementation:**

```python
def effective_spread(trade_price, sign, mid_at_trade):
    return 2 * sign * (trade_price - mid_at_trade)

def realized_spread(trade_price, sign, mid_future, mid_at_trade):
    """mid_future = mid 5 minutes (or 30s for HFT) AFTER the trade."""
    return 2 * sign * (trade_price - mid_future)

def roll_spread(price_changes: pd.Series) -> float:
    """Roll (1984), Journal of Finance 39(4), 1127-1139.
    Returns implied spread from negative serial covariance of returns."""
    cov = price_changes.diff().cov(price_changes.diff().shift(1))
    return float(2.0 * np.sqrt(-cov)) if cov < 0 else float("nan")
```

**Pitfalls.**
- Mismatched `mid_at_trade`: must be the mid *just before* the trade prints,
  not the mid that includes the trade's impact. Use `merge_asof` with
  `direction='backward'` and a tolerance of microseconds.
- Roll's estimator returns NaN when the autocovariance is positive; that's
  a feature, not a bug — it tells you the data has trend autocorrelation that
  violates Roll's assumptions, and you shouldn't quote a spread from it.

## Order flow dynamics — Hawkes intensity

**Intuition.** Trade arrivals cluster — a buy market-order makes another buy
market-order more likely in the next 100 ms, because both are responses to
the same information shock. A Hawkes process is a self-exciting point process
that captures this: every event raises the conditional arrival intensity by
a kernel-weighted amount that decays over time.

**Math.** Univariate self-exciting Hawkes process with exponential kernel:

```
λ(t) = μ + Σ_{t_i < t} α × exp(-β × (t - t_i))
```

`μ` is baseline intensity, `α` is the self-excitation, `β` the decay rate.
Stability requires `α/β < 1`. The bivariate case (separate buy and sell
intensities with cross-excitation between them) is the standard Bacry-
Mastromatteo-Muzy (2015) setting.

**Implementation (using the `tick` library):**

```python
# pip install tick   (Bacry-Iutzeler-Mastromatteo-Bompaire 2017)
from tick.hawkes import HawkesExpKern

def fit_hawkes_buy_sell(buy_times: np.ndarray, sell_times: np.ndarray,
                       decay: float = 5.0):
    """Fit a 2-dim Hawkes process with one decay constant.

    buy_times, sell_times: 1-D arrays of event timestamps in seconds.
    decay: β in 1/seconds. Tune on a small grid by likelihood.

    Reference: Bacry, Mastromatteo, Muzy (2015), Market Microstructure and
    Liquidity 1(01), 1550005. arXiv:1502.04592.
    """
    learner = HawkesExpKern(decays=decay)
    learner.fit([[buy_times, sell_times]])
    return {
        "baseline": learner.baseline,         # shape (2,)
        "adjacency": learner.adjacency,       # shape (2, 2) — self + cross
        "score": learner.score(),
    }
```

**Interpretation.** The adjacency matrix's diagonal entries are the
self-excitation of buys-by-buys and sells-by-sells; off-diagonals are
cross-excitation. A diagonal entry near 1.0 means strong clustering (your
arrival-rate model needs Hawkes, not Poisson); cross-excitation tells you
whether buys and sells are reactive to each other or independent regimes.

**Pitfalls.**
- Decay parameter `β` is critical and not estimated jointly in `HawkesExpKern`
  (it's a fixed argument). Tune on a small grid; mis-specified decay
  silently biases the adjacency.
- Hawkes likelihood is non-convex; refit with different initialisations on
  long histories.
- Sub-millisecond timestamp granularity matters. Microsecond timestamps cast
  to floats lose precision over hours of trading — use seconds-since-anchor.
