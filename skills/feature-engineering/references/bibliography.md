# Feature Engineering — References & Bibliography

Full source list for the methodology in `SKILL.md`.

## Primary libraries
This skill is methodology-first; operational implementations live across `mlfinlab`, `ta-lib`, `ta`, and `pandas` rolling-window operators.

- [mlfinlab on GitHub](https://github.com/hudson-and-thames/mlfinlab) — Hudson & Thames implementation of Lopez de Prado's AFML; triple-barrier, fractional differencing, sample weights
- [mlfinlab documentation](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/) — pinned to v1.x
- [ta-lib-python on GitHub](https://github.com/TA-Lib/ta-lib-python) — Python bindings to the C TA-Lib library; 200+ indicators, very fast
- [ta (Bukosabino) on GitHub](https://github.com/bukosabino/ta) — pure-Python pandas-native alternative; slower but no native install
- [pandas documentation](https://pandas.pydata.org/docs/) — `rolling`, `expanding`, `shift`, `groupby` are the leakage-safety toolset

## Deep-dive docs (specific pages worth bookmarking)
- [mlfinlab Labeling module (triple-barrier)](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/labeling/labeling.html) — canonical implementation of the snippet above; verify your version's API
- [mlfinlab Fractional Differentiation](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/feature_engineering/fracdiff_features.html) — both fixed-width (truncated) and expanding-window variants
- [mlfinlab Sample Weights](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/sample_weights/sample_weights.html) — uniqueness + return attribution weights
- [mlfinlab Structural Breaks](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/structural_breaks/introduction.html) — CUSUM event filters that generate the `events` index for triple-barrier
- [mlfinlab Information-Driven Bars](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/sample_data/information_driven_bars.html) — dollar/volume/imbalance bars; the right "samples" for triple-barrier on intraday data
- [ta-lib indicator reference](https://ta-lib.github.io/ta-lib-python/funcs.html) — the 200+ indicators with parameter docs
- [ta library reference](https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html) — every momentum / volatility / volume indicator; `add_all_ta_features` convenience function
- [pandas `rolling` window docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html) — right-aligned by default; the leakage-safety guarantee

## Adjacent / alternative libraries
- [tsfresh](https://github.com/blue-yonder/tsfresh) — automated time-series feature extraction; 4000+ features over rolling windows
- [feature-engine](https://github.com/feature-engine/feature_engine) — sklearn-compatible feature engineering pipelines; useful for the ColumnTransformer / Pipeline contract
- [stumpy](https://github.com/TDAmeritrade/stumpy) — matrix profile features; useful when "this pattern repeats" is the signal
- [pyts](https://github.com/johannfaouzi/pyts) — time-series feature engineering (BOSS, SAX, shapelets) and classification baselines
- [riskfolio-lib](https://github.com/dcajasn/Riskfolio-Lib) — when "features" become portfolio constraints (factor exposures)
- [statsmodels.tsa.stattools.adfuller](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html) — ADF test used in deciding the right fractional-differencing `d` parameter

## Academic papers
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. ISBN 9781119482086 — the bible of this skill.
  - Ch. 3 — Labeling (triple-barrier method)
  - Ch. 4 — Sample weights for overlapping labels
  - Ch. 5 — Fractional differencing
  - Ch. 7 — Purged/embargoed cross-validation (see `model-evaluation`)
- Cont, R., Kukanov, A., & Stoikov, S. (2014). "The Price Impact of Order Book Events." *Journal of Financial Econometrics* 12(1), 47-88. [DOI: 10.1093/jjfinec/nbt003](https://doi.org/10.1093/jjfinec/nbt003) — OFI feature.
- Hasbrouck, J. (2007). *Empirical Market Microstructure*. Oxford University Press. ISBN 9780195301649 — background for tick-data features and microstructure noise.
- Easley, D., López de Prado, M. M., & O'Hara, M. (2012). "Flow Toxicity and Liquidity in a High-Frequency World." *Review of Financial Studies* 25(5), 1457-1493. [SSRN 1695596](https://papers.ssrn.com/abstract=1695596) — VPIN, dollar / volume bars.
- Hosking, J. R. M. (1981). "Fractional Differencing." *Biometrika* 68(1), 165-176. [DOI: 10.2307/2335817](https://doi.org/10.2307/2335817) — the original fractional differencing paper that Ch. 5 of AFML builds on.
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2014). "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance." *Notices of the AMS* 61(5), 458-471. [SSRN 2326253](https://papers.ssrn.com/abstract=2326253) — why "feature engineering" alone can produce false discoveries; pairs with `ml-hypothesis-design`.
- Easley, D., Kiefer, N. M., O'Hara, M., & Paperman, J. B. (1996). "Liquidity, Information, and Infrequently Traded Stocks." *Journal of Finance* 51(4), 1405-1436. [DOI: 10.1111/j.1540-6261.1996.tb04074.x](https://doi.org/10.1111/j.1540-6261.1996.tb04074.x) — PIN; theoretical foundation for the toxic-flow microstructure features.
- Bouchaud, J.-P., Bonart, J., Donier, J., & Gould, M. (2018). *Trades, Quotes and Prices: Financial Markets Under the Microscope*. Cambridge UP. ISBN 9781107156050 — modern empirical microstructure; the impact / OFI / queue chapters complement Hasbrouck.
- Ferreira, M. A., & Santa-Clara, P. (2011). "Forecasting Stock Market Returns: The Sum of the Parts Is More Than the Whole." *Journal of Financial Economics* 100(3), 514-537. [DOI: 10.1016/j.jfineco.2011.02.003](https://doi.org/10.1016/j.jfineco.2011.02.003) — feature-decomposition arguments; useful for thinking about which features carry edge.
- Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). "Value and Momentum Everywhere." *Journal of Finance* 68(3), 929-985. [DOI: 10.1111/jofi.12021](https://doi.org/10.1111/jofi.12021) — the canonical feature-as-factor reference for cross-sectional features.

## Tutorials & write-ups
- [Hudson & Thames Advances in Financial ML series](https://hudsonthames.org/articles/) — operational write-ups for every chapter of AFML
- [QuantConnect feature engineering tutorials](https://www.quantconnect.com/research/) — full pipelines with QuantConnect data
- [Marcos Lopez de Prado lectures (Cornell)](https://github.com/cornell-tech/financial-data-science) — pairing slides + code with AFML chapters
- [Stefan Jansen's Machine Learning for Trading book repo](https://github.com/stefan-jansen/machine-learning-for-trading) — the broadest open-source feature pipeline catalog

## Standard datasets / benchmarks
- The "100 random features" reproducibility test — generate 100 random walks, label them with triple-barrier, fit a model, compute deflated Sharpe; should reject all features. The standard sanity check for label/feature independence.
- AFML Ch. 3 example data — Dollar bar reconstruction from TAQ; the canonical reproduction case
- yfinance equity universe with point-in-time S&P 500 membership (CRSP for institutional) — the standard avoid-survivorship-bias benchmark

## Last cross-checked
2026-05-20 — via WebSearch verification of all paper DOIs + cross-check of mlfinlab / ta-lib / ta API surfaces.
