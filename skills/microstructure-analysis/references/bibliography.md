# References and datasets

Full bibliography, library pointers, and dataset list for the microstructure skill.
`SKILL.md` keeps only the cross-links it needs at decision time; this file is the
durable reference.

## Primary libraries

This skill is methodology-first; operational implementations live in domain libraries.
The canonical ones:

- [mlfinlab on GitHub](https://github.com/hudson-and-thames/mlfinlab) — Hudson & Thames implementation of Lopez de Prado's AFML; includes VPIN, dollar bars / volume bars, Kyle's lambda, microstructural information features
- [mlfinlab `microstructural_features`](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/feature_engineering/microstructural_features.html) — Kyle's lambda, Amihud's lambda, Hasbrouck's lambda, VPIN, all in one place
- [nautilus_trader on GitHub](https://github.com/nautechsystems/nautilus_trader) — the live-execution layer; `OrderBook`, `subscribe_order_book_deltas`, `OrderBookImbalance` strategy template
- [tardis-machine](https://github.com/tardis-dev/tardis-machine) — historical L2/L3 + tick data backbone; the input layer for everything in this skill

## Deep-dive docs (specific pages worth bookmarking)

- [mlfinlab Triple-Barrier method](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/labeling/labeling.html) — what to do with the trade-direction signs once you have them; pairs with `feature-engineering`
- [mlfinlab Information-Driven Bars](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/sample_data/information_driven_bars.html) — VPIN, volume-imbalance, dollar-imbalance bars (Easley/Lopez de Prado/O'Hara)
- [nautilus_trader `OrderBook` API](https://docs.nautilustrader.io/api_reference/model/orderbook.html) — `apply_deltas`, `best_bid_price`, `imbalance`; the production-grade book object
- [pandas `merge_asof`](https://pandas.pydata.org/docs/reference/api/pandas.merge_asof.html) — the canonical operator for trade ↔ quote matching at controlled lag
- [Databento docs on MBO data](https://databento.com/docs/standards-and-conventions/normalization) — the L3 (market-by-order) schema that gives exact queue position

## Adjacent / alternative libraries

- [highfrequency (R)](https://github.com/jonathancornelissen/highfrequency) — the R-language reference for realized variance, microstructure noise estimators; Hasbrouck-school implementations
- [pyhrvanalysis / tickbylimit](https://github.com/cnntk/tickbylimit) — niche; useful for queue-position simulation
- [polars / vaex](https://github.com/pola-rs/polars) — when pandas can't handle the L2 data volume; `merge_asof` equivalents available
- [duckdb](https://github.com/duckdb/duckdb) — out-of-core SQL over Parquet for the same purpose; pairs naturally with tardis-machine output

## Academic papers

- Lee, C. M. C., & Ready, M. J. (1991). "Inferring Trade Direction from Intraday Data." *Journal of Finance* 46(2), 733-746. [DOI: 10.1111/j.1540-6261.1991.tb02683.x](https://doi.org/10.1111/j.1540-6261.1991.tb02683.x) — the Lee-Ready algorithm; the trade-direction classification standard.
- Kyle, A. S. (1985). "Continuous Auctions and Insider Trading." *Econometrica* 53(6), 1315-1335. [JSTOR 1913210](https://www.jstor.org/stable/1913210) — Kyle's lambda; the price-impact-of-flow framework.
- Cont, R., Kukanov, A., & Stoikov, S. (2014). "The Price Impact of Order Book Events." *Journal of Financial Econometrics* 12(1), 47-88. [DOI: 10.1093/jjfinec/nbt003](https://doi.org/10.1093/jjfinec/nbt003) / [arXiv:1011.6402](https://arxiv.org/abs/1011.6402) — OFI; the dynamic-flow alternative to static book imbalance.
- Easley, D., López de Prado, M. M., & O'Hara, M. (2012). "Flow Toxicity and Liquidity in a High-Frequency World." *Review of Financial Studies* 25(5), 1457-1493. [SSRN 1695596](https://papers.ssrn.com/abstract=1695596) — VPIN; the volume-clock toxicity estimator.
- Easley, D., Kiefer, N. M., O'Hara, M., & Paperman, J. B. (1996). "Liquidity, Information, and Infrequently Traded Stocks." *Journal of Finance* 51(4), 1405-1436. [DOI: 10.1111/j.1540-6261.1996.tb04074.x](https://doi.org/10.1111/j.1540-6261.1996.tb04074.x) — PIN; the predecessor to VPIN, useful as theoretical foundation.
- Ellis, K., Michaely, R., & O'Hara, M. (2000). "The Accuracy of Trade Classification Rules: Evidence from Nasdaq." *Journal of Financial and Quantitative Analysis* 35(4), 529-551. [DOI: 10.2307/2676254](https://doi.org/10.2307/2676254) — EMO classifier; one of the Lee-Ready alternatives.
- Hasbrouck, J. (2007). *Empirical Market Microstructure: The Institutions, Economics, and Econometrics of Securities Trading*. Oxford University Press. ISBN 9780195301649 — the canonical academic textbook; Chapters on Roll model, sequential trade models, and PIN are essential prerequisites.
- O'Hara, M. (1995). *Market Microstructure Theory*. Blackwell. ISBN 9781557864437 — the theory companion to Hasbrouck.
- Bouchaud, J.-P., Bonart, J., Donier, J., & Gould, M. (2018). *Trades, Quotes and Prices: Financial Markets Under the Microscope*. Cambridge UP. ISBN 9781107156050 — modern empirical microstructure with the European HFT lens; OFI / impact / order-book dynamics.
- Lopez de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. Chapters 2-3 — dollar/volume/information-driven bars + triple-barrier labeling for tick-rate signals.

## Tutorials & write-ups

- [Cont, Kukanov, Stoikov OFI explainer notebook (community)](https://github.com/jaungiers/OFI-Implementation) — clean reference reproduction of the original paper's results
- [Easley, Lopez de Prado, O'Hara VPIN reference page](https://www.davidhbailey.com/dhbpapers/) — slides and ungated drafts
- [Hudson & Thames "VPIN and Order Flow Toxicity"](https://hudsonthames.org/) — practical write-up with mlfinlab code

## Standard datasets / benchmarks

- LOBSTER limit order book data — [lobsterdata.com](https://lobsterdata.com/) — the academic standard for L2/L3 microstructure research
- Tardis crypto L2 archives — [tardis.dev](https://tardis.dev/) — the canonical 24/7 crypto book dataset
- TAQ (NYSE) — for equities; institutional-only access but the historical gold standard
- Databento real-time + historical MBO — [databento.com](https://databento.com/) — full L3 with order IDs, exact queue position recoverable
- Flash Crash 2010 (May 6) E-mini S&P 500 — the canonical VPIN validation case; the spike preceded liquidity withdrawal

## Last cross-checked

2026-05-20 — via WebSearch verification of all paper DOIs/JSTOR links + cross-check of mlfinlab and nautilus_trader API surfaces.
