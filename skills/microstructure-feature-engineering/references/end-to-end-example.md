# End-to-end example

Goal: build a feature matrix for a short-horizon model on **BTC-USD perp**, Hyperliquid tape + L2, using 100-volume-coin bars, with OFI + micro-price + HMM-state + triple-barrier labels. Output stored as parquet.

Functions used (`volume_bars`, `ofi_bar_aligned`, `weighted_mid`, `rv_bipower`, `trade_sign_autocorr`, `hmm_state_feature`, `assemble_feature_matrix`, `triple_barrier_micro`) are defined in `bar-construction.md` and `feature-families.md`.

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
