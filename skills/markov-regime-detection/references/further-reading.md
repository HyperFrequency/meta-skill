# References & Further Reading

## Primary library
- [hmmlearn on GitHub](https://github.com/hmmlearn/hmmlearn) — upstream repo, issues, releases
- [hmmlearn documentation (stable)](https://hmmlearn.readthedocs.io/en/stable/) — pinned to v0.3.x as of cross-check
- [hmmlearn tutorial](https://hmmlearn.readthedocs.io/en/stable/tutorial.html) — Baum-Welch / Viterbi walkthrough
- [hmmlearn API reference](https://hmmlearn.readthedocs.io/en/stable/api.html) — full signature for every emission family
- [hmmlearn auto_examples](https://hmmlearn.readthedocs.io/en/stable/auto_examples/index.html) — Gaussian, multinomial, sampling, and the canonical "regime switching" example

## Deep-dive docs (specific pages worth bookmarking)
- [`GaussianHMM` API](https://hmmlearn.readthedocs.io/en/stable/api.html#hmmlearn.hmm.GaussianHMM) — `covariance_type`, `means_prior`, `covars_prior`; the regularization knobs that matter for small samples
- [`CategoricalHMM` API](https://hmmlearn.readthedocs.io/en/stable/api.html#hmmlearn.hmm.CategoricalHMM) — `n_features` semantics; why you must set it manually for fixed alphabets
- [`GMMHMM` API](https://hmmlearn.readthedocs.io/en/stable/api.html#hmmlearn.hmm.GMMHMM) — Gaussian-mixture emissions per state; richer per-state distributions
- [`ConvergenceMonitor`](https://hmmlearn.readthedocs.io/en/stable/api.html#hmmlearn.base.ConvergenceMonitor) — `history` attribute traces per-iteration log-likelihood; the right way to debug EM
- [Score / decode / sample methods](https://hmmlearn.readthedocs.io/en/stable/api.html#hmmlearn.base.BaseHMM.score) — log-likelihood, Viterbi vs MAP decoding, generative sampling
- [Variational HMM API](https://hmmlearn.readthedocs.io/en/stable/api.html#hmmlearn.vhmm.VariationalCategoricalHMM) — variational-Bayes alternative to EM when point estimates aren't enough

## Adjacent / alternative libraries
- [statsmodels `tsa.regime_switching`](https://www.statsmodels.org/stable/tsa.html#markov-regime-switching) — `MarkovRegression`, `MarkovAutoregression`; supports exogenous regressors and AR dynamics within states (what `hmmlearn` lacks)
- [pomegranate](https://github.com/jmschrei/pomegranate) — actively-maintained HMM/Bayes net library with GPU support and more flexible emission families
- [pyhsmm](https://github.com/mattjj/pyhsmm) — Bayesian non-parametric HMMs (HDP-HMM, sticky HDP-HMM); for state-count selection without manual tuning
- [hsmmlearn](https://github.com/jvkersch/hsmmlearn) — hidden semi-Markov models when state durations are not geometric
- [numpyro / PyMC HMM examples](https://www.pymc.io/projects/examples/en/latest/case_studies/hierarchical_partial_pooling.html) — fully Bayesian HMM with posterior over transition matrices when you need uncertainty quantification

## Academic papers
- Rabiner, L. R. (1989). "A Tutorial on Hidden Markov Models and Selected Applications in Speech Recognition." *Proceedings of the IEEE* 77(2), 257-286. [DOI: 10.1109/5.18626](https://doi.org/10.1109/5.18626) — the canonical HMM tutorial; reading once is mandatory.
- Hamilton, J. D. (1989). "A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle." *Econometrica* 57(2), 357-384. [JSTOR 1912559](https://www.jstor.org/stable/1912559) — Markov regime switching as applied to economic series; the financial-application origin.
- Bilmes, J. A. (1998). "A Gentle Tutorial of the EM Algorithm and its Application to Parameter Estimation for Gaussian Mixture and Hidden Markov Models." TR-97-021, ICSI Berkeley. [PDF](https://f.hubspotusercontent40.net/hubfs/8111846/Imported_Blog_Media/em.pdf) — the cleanest derivation of Baum-Welch as instance of EM; bridges the Rabiner-Hamilton notation gap.
- Hamilton, J. D. (1990). "Analysis of Time Series Subject to Changes in Regime." *Journal of Econometrics* 45(1-2), 39-70. [DOI: 10.1016/0304-4076(90)90093-9](https://doi.org/10.1016/0304-4076(90)90093-9) — the filter/smoother derivation specifically for switching ARMA models.
- Ang, A., & Bekaert, G. (2002). "Regime Switches in Interest Rates." *Journal of Business & Economic Statistics* 20(2), 163-182. [DOI: 10.1198/073500102317351930](https://doi.org/10.1198/073500102317351930) — the canonical finance application of multivariate Markov-switching.
- Fox, E. B., Sudderth, E. B., Jordan, M. I., & Willsky, A. S. (2011). "A Sticky HDP-HMM with Application to Speaker Diarization." *Annals of Applied Statistics* 5(2A), 1020-1056. [DOI: 10.1214/10-AOAS395](https://doi.org/10.1214/10-AOAS395) — for when you want to learn the number of states from data.

## Tutorials & write-ups
- [hmmlearn "Gaussian HMM of stock data" example](https://hmmlearn.readthedocs.io/en/stable/auto_examples/plot_hmm_stock_analysis.html) — the canonical finance use case, end to end
- [Statsmodels Markov-switching documentation page](https://www.statsmodels.org/stable/examples/notebooks/generated/markov_regression.html) — Hamilton (1989) model fully reproduced with exogenous variables
- [PyMC HMM case study](https://www.pymc.io/projects/examples/en/latest/case_studies/hierarchical_partial_pooling.html) — Bayesian alternative when sample size is small

## Standard datasets / benchmarks
- US GDP growth 1947-present from FRED — Hamilton's original two-state recession indicator dataset; standard reproducibility benchmark
- S&P 500 daily returns spanning 2007-2010 — fits a clean 3-state HMM (pre-crisis / crisis / recovery); useful for testing convergence and state interpretability
- Old Faithful eruption durations — classic two-state mixture; included in many tutorials as the "definitely converges" sanity check

## Last cross-checked
2026-05-20 — via Context7 `/websites/hmmlearn_readthedocs_io_en_stable` (553 snippets, High, benchmark 85.4) + WebSearch verification of all paper DOIs/JSTOR links + Auggie cross-check of `HyperFrequency/hmmlearn` fork source (`src/hmmlearn/hmm.py`, `_emissions.py`, tests).
