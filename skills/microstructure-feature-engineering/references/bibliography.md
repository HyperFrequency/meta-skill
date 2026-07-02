# References and datasets

## Primary library

- `mlfinlab` (Hudson & Thames). Last fully-open-source version: `0.x` series (≈2021). Implements `data_structures` (tick/volume/dollar/imbalance bars), `labeling.triple_barrier`, `features.fracdiff`, `cross_validation.PurgedKFold`. Source: <https://github.com/hudson-and-thames/mlfinlab>. **Verified state:** the package moved to a closed-source / paid-tier model after the v0.x series; the OSS v0.x API is the reference here. Confirm current install path before pinning.

## Deep-dive docs

- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. ISBN 978-1119482086. Chapters 2 (information-driven bars), 3 (triple-barrier labeling), 4 (sample uniqueness, sample weights), 5 (fractional differencing), 7 (purged + embargoed CV).
- `hmmlearn` user guide for `GaussianHMM`: <https://hmmlearn.readthedocs.io>. **Verify** `n_iter` / `covariance_type` defaults against the installed version.

## Adjacent libraries

- `tick` (Bacry et al.) — `HawkesExpKern`, `HawkesSumExpKern`. <https://github.com/X-DataInitiative/tick>. **Note:** `adjacency` in the `tick` exponential-kernel parameterization is already the branching-ratio (kernel integral). Other libraries (`hawkeslib`, `pyhawkes`) parameterize differently.
- `nautilus_trader` — L2/L3 ingest via `OrderBookDelta`; the canonical execution-side reimplementation target for any feature pipeline that needs to run live.
- `statsmodels` — ADF (`adfuller`), KPSS (`kpss`); standard stationarity tests.
- `vectorbt` / `vectorbt-pro` — bar-level backtest consumer; respects custom bar indexes if you persist them.

## Academic papers

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

## Tutorials

- Hudson & Thames blog + notebooks (open-source archive) — worked `mlfinlab` bars and triple-barrier examples. <https://hudsonthames.org>.

## Standard datasets

- **Databento** — MBO/MBP-10/MBP-1 for US equities, futures, options. Canonical L3 source.
- **Tardis.dev** — tape + L2/L3 for crypto (Binance, Hyperliquid, OKX, Bybit, …).
- **LOBSTER** — academic NASDAQ LOB reconstructions; standard in microstructure-noise benchmarks.

## Unverified / flagged

- `mlfinlab` API beyond v0.x is **not verified** here — Context7 only returned `requirements.txt`, and the package moved closed-source post-v0.x. Treat v0.x as the reference; query the installed version's docstrings before pinning specific function names.
- `tick`'s `HawkesExpKern.adjacency` semantics asserted above (branching-ratio for normalized exponential kernels) should be re-confirmed against the installed version — API churn between 0.6.x and 0.7.x.

**Last cross-checked:** 2026-05-20
