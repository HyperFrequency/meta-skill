# Evaluating Synthetic Series

Marginal stats (mean / std / kurtosis) are necessary but not sufficient. The checklist that catches most fakes:

| Check | Reasonable test |
|---|---|
| Marginal moments | `np.mean`, `np.std`, `scipy.stats.kurtosis` — within 10% of real |
| Autocorrelation | `statsmodels.tsa.stattools.acf(samples, nlags=20)` matches real at lags 1-5 |
| Volatility clustering | ACF of squared returns — most return series show slow decay; vanilla GAN usually misses this, TimeGAN can capture it |
| Fat tails | QQ-plot against real returns; or compare 1st/99th percentiles |
| Two-sample test | Kolmogorov-Smirnov or Anderson-Darling: real-vs-fake |
| Downstream task | Train your strategy on fake-only data, evaluate on real. Sharpe degradation tells you how useful the GAN actually is |

If any of these fail, do not use the samples for backtesting. A GAN that matches mean and std but has zero kurtosis is *worse than Gaussian noise* for stress tests.
