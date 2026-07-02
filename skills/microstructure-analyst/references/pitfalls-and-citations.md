# Consolidated pitfalls + citations

## Consolidated common pitfalls

Numbered for cross-reference from the section reference files.

**P1. Sequence-gap silent recovery.** A websocket reconnect that re-fires
old deltas without a snapshot leaves your book inconsistent. *Always* go
snapshot → buffered-deltas → resume. Never trust "we're back online" alone.

**P2. Tape vs book clock skew.** Trade prints and book updates can come from
different streams with different latencies. A naive merge-asof against the
book *as of the trade's ts_event* can attach a quote that the system hadn't
yet seen at trade time. Use `ts_init` for "what we knew at decision time" and
`ts_event` for causality, and document which one you used.

**P3. Look-ahead bias in BVC volume buckets.** BVC requires *complete* volume
buckets. If you label the in-progress bucket using its eventual close-price
return, you've leaked the bucket's own return into the classifier. Only
emit BVC for closed buckets, lagging the label by one bucket.

**P4. Sub-tick price reconstruction errors.** If a venue quotes in 0.1 ticks
and you parse JSON via `float`, you get drift like `64512.299999...`. Use
`Decimal` at the parser boundary and round to the venue's `tick_size` grid
before storing. NautilusTrader handles this in Rust; ad-hoc Python parsers
do not.

**P5. Static imbalance ≠ OFI.** They have different signs in queue-build-up
vs sweep regimes. A backtest that uses `I_top` where `OFI` was intended (or
vice versa) can have the right *direction* in 70% of regimes and the wrong
direction in 30%, which is hard to debug from PnL alone.

**P6. Treating spoofing detectors as alpha.** They're throttles, not directional
signals. If you sell when spoofing fires, you're acting *with* the spoofer.
Use the signal to widen quotes or step out, never to take.

**P7. FIFO assumption on a pro-rata venue.** Some CME options venues, the
Eurex options book, and certain CME futures use pro-rata or hybrid matching.
A FIFO queue-position estimate on a pro-rata venue is wrong in a way that
mostly *helps* the backtest — passive fills appear easier than reality.
Read the venue spec.

**P8. Hidden orders / iceberg fills.** L2 size shows only displayed depth.
Reconcile trade volume against displayed depth consumed; a persistent positive
residual is hidden liquidity that your indicators are blind to.

**P9. Aggregating event-time OFI on wall-clock windows.** Bins of "1 second
of wall-clock" contain wildly different numbers of events in burst vs quiet
regimes. Aggregate OFI in event-count or trade-volume bins for stable
regressions; use wall-clock only as a downstream feature.

**P10. Hawkes decay parameter assumed not estimated.** `HawkesExpKern`'s
`decays` argument is fixed at fit time. Mis-specified decay silently biases
the adjacency matrix. Sweep over `decay ∈ {1, 2, 5, 10, 30}` seconds and
take the best-likelihood fit.

---

## References

**Primary library / Deep-dive docs (verified via Context7 last cross-check
date, see bottom of file).**

- NautilusTrader documentation, `docs.nautilustrader.io` and the in-repo
  `nautilus_trader/docs/api_reference/backtest.md`. `BacktestEngine`,
  `LatencyModel` / `LatencyModelConfig`, `FillModel`, `OrderBookDeltas`,
  `BookType`, `OrderBookL1_MBP`/`L2_MBP`/`L3_MBO`. Verified via Context7
  `/nautechsystems/nautilus_trader`.
- `hftbacktest` documentation, `https://hftbacktest.readthedocs.io/`.
  `BacktestAsset`, `ROIVectorMarketDepthBacktest`, `power_prob_queue_model`,
  `intp_order_latency`, `trading_value_fee_model`. Verified via Context7
  `/nkaz001/hftbacktest`.
- Polars user guide, `https://docs.pola.rs/`. `scan_csv`, lazy / streaming
  execution, `iter_slices`.
- DuckDB documentation, `https://duckdb.org/docs/`. `read_csv_auto`, parquet
  scans, predicate pushdown.
- `tick` library, `https://x-datainitiative.github.io/tick/`. `HawkesExpKern`,
  multivariate point processes.
- `databento-python`, `https://databento.com/docs/`. `DBNStore`, schemas
  (`mbp-1`, `mbp-10`, `mbo`).

**Adjacent libraries.**

- `mlfinlab` (`https://github.com/hudson-and-thames/mlfinlab`) — canonical
  Lopez de Prado reference. BVC, fractional differentiation, triple-barrier,
  Kyle's lambda. Research-license only.
- `vectorbt` / `vectorbt-pro` — see the in-repo `vectorbt` skill for the
  full surface.

**Academic papers (each verified to exist at last cross-check).**

- Lee, C. M. C., & Ready, M. J. (1991). Inferring Trade Direction from Intraday
  Data. *Journal of Finance*, 46(2), 733–746.
  DOI: 10.1111/j.1540-6261.1991.tb02683.x. Verified.
- Kyle, A. S. (1985). Continuous Auctions and Insider Trading. *Econometrica*,
  53(6), 1315–1335. Verified.
- Roll, R. (1984). A Simple Implicit Measure of the Effective Bid-Ask Spread
  in an Efficient Market. *Journal of Finance*, 39(4), 1127–1139.
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The Price Impact of Order
  Book Events. *Journal of Financial Econometrics*, 12(1), 47–88.
  DOI: 10.1093/jjfinec/nbt003. arXiv:1011.6402.
  Verified via WebFetch of `arxiv.org/abs/1011.6402` (title, authors,
  venue match).
- Easley, D., López de Prado, M. M., & O'Hara, M. (2012). Flow Toxicity and
  Liquidity in a High-Frequency World. *Review of Financial Studies*, 25(5),
  1457–1493. SSRN: 1695596. Verified by metadata via WebSearch
  (SSRN direct fetch returned HTTP 403; this is a captcha block, not a
  missing paper).
- Easley, D., López de Prado, M. M., & O'Hara, M. (2016). Discerning
  Information from Trade Data. *Journal of Financial Economics*, 120(2),
  269–286. SSRN: 1989555. Verified via WebSearch.
- Stoikov, S. (2018). The micro-price: a high-frequency estimator of future
  prices. *Quantitative Finance*, 18(12), 1959–1966.
  DOI: 10.1080/14697688.2018.1489139. SSRN: 2970694. Verified via WebSearch.
- Bacry, E., Mastromatteo, I., & Muzy, J.-F. (2015). Hawkes Processes in
  Finance. *Market Microstructure and Liquidity*, 1(01), 1550005.
  arXiv:1502.04592. Verified via WebSearch (title, authors, journal match).
- Lee, E. J., Eom, K. S., & Park, K. S. (2013). Microstructure-Based
  Manipulation: Strategic Behavior and Performance of Spoofing Traders.
  *Journal of Financial Markets*, 16, 227–252.
  SSRN: 1328899. Verified via WebSearch.
- Tao, X., Day, A., Ling, L., & Drapeau, S. (2020). On Detecting Spoofing
  Strategies in High Frequency Trading. arXiv:2009.14818. Verified via
  WebSearch.
- Hasbrouck, J. (2007). *Empirical Market Microstructure*. Oxford University
  Press. ISBN 9780195301649.
- O'Hara, M. (1995). *Market Microstructure Theory*. Blackwell.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
  Chapter 19 covers microstructure features in production.

**Tutorials and explanatory notes (use with skepticism — none have the
authority of the journal-published papers above).**

- Stoikov micro-price intuition note: `https://arxiv.org/pdf/2307.15599`
  ("Understanding the worst-kept secret of high-frequency trading") —
  Pulido's commentary on the micro-price; provides a clean derivation.

**Standard datasets.**

- Tardis (`tardis.dev`) — crypto venues, L2 / L3 / trades / funding /
  liquidations. Wired in this repo via the `tardis-data-agent` skill.
- Databento — US equities, futures, options. Best-in-class L3 / MBO for
  US listed markets.
- Polygon.io — US equities and options flat files. Cheaper than Databento;
  fewer schema niceties.
- CME DataMine — futures and options on futures, MBO available.

**Last cross-checked:** 2026-05-20. NautilusTrader API confirmed against
`develop`-branch docs via Context7. `hftbacktest` API confirmed via Context7
against the `nkaz001/hftbacktest` examples notebooks. All academic citations
re-verified against arXiv / journal metadata via WebSearch + WebFetch.
