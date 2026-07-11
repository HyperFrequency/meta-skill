# Complexity, Entropy, and Fractal Analysis

These measures quantify irregularity, self-similarity, and multiscale structure
of a time series. They apply to any signal (HRV tachogram, EEG, EDA, ...). Many
depend on phase-space embedding parameters — optimize those first, and always
report the parameters you used.

## Broad sweep

```python
indices = nk.complexity(signal, sampling_rate=1000, show=False)
```

Returns a DataFrame of many entropy, fractal, and nonlinear measures at once —
useful for exploration before committing to specific metrics.

## Embedding-parameter optimization

Run these before entropy / attractor measures:

- `nk.complexity_delay(signal, delay_max=100, method='fraser1986')` — time delay
  τ. Methods: `'fraser1986'` (mutual-information first minimum), `'theiler1990'`
  (autocorrelation first zero), `'casdagli1991'`.
- `nk.complexity_dimension(signal, delay=None, dimension_max=20, method='afn')` —
  embedding dimension m. Methods: `'afn'` (averaged false nearest neighbors),
  `'fnn'`, `'correlation'`.
- `nk.complexity_tolerance(signal, method='sd')` — tolerance r for ApEn/SampEn.
  `'sd'` (0.1–0.25 × SD is conventional), `'maxApEn'`, `'recurrence'`.
- `nk.complexity_k(signal, k_max=20)` — k for Higuchi fractal dimension.

Common defaults when not optimizing: τ = 1 (HRV), m = 2–3, r = 0.2 × SD.

## Entropy — `nk.entropy_*`

- `entropy_shannon(signal)` — classical information content (bits).
- `entropy_approximate(signal, delay=1, dimension=2, tolerance='sd')` — ApEn;
  regularity, but length-sensitive (≥ 100–300 pts).
- `entropy_sample(signal, delay=1, dimension=2, tolerance='sd')` — SampEn;
  length-robust, no self-match bias — preferred over ApEn.
- `entropy_multiscale(signal, scale=20, dimension=2, tolerance='sd', method='MSEn')`
  — MSE across coarse-graining scales; `'MSEn'`, `'MSApEn'`, `'CMSE'`, `'RCMSE'`.
  Distinguishes true complexity from noise (white noise falls off across scales;
  structured signals hold up).
- `entropy_fuzzy(...)` — fuzzy membership, stable on short/noisy signals.
- `entropy_permutation(signal, delay=1, dimension=3)` — ordinal-pattern entropy;
  fast, noise-robust; common in EEG / anesthesia depth.
- `entropy_spectral(signal, sampling_rate, bands=None)` — normalized entropy of
  the power spectrum (0 = pure tone, 1 = white noise).
- `entropy_svd(...)`, `entropy_differential(...)`, `entropy_tsallis(signal, q=2)`,
  `entropy_renyi(signal, alpha=2)`, plus specialized variants
  (`entropy_dispersion`, `entropy_range`, `entropy_slope`, `entropy_increment`,
  `entropy_phase`, `entropy_attention`, `entropy_grid`,
  `entropy_symbolicdynamic`, `entropy_rate`, `entropy_cumulative_residual`,
  `entropy_quadratic`).

## Fractal dimension — `nk.fractal_*`

- `fractal_katz(signal)`, `fractal_petrosian(signal)`, `fractal_sevcik(signal)`,
  `fractal_nld(signal)` — fast waveform-complexity estimators (1 = line, higher
  = rougher).
- `fractal_higuchi(signal, k_max=10)` — self-similarity; common in EEG/HRV and
  epilepsy detection.
- `fractal_psdslope(signal, sampling_rate)` — log-log PSD slope β (≈0 white,
  ≈−1 pink/1-f, ≈−2 brown).
- `fractal_hurst(signal)` — Hurst exponent (H < 0.5 mean-reverting, 0.5 random
  walk, > 0.5 persistent long-memory).
- `fractal_correlation(signal, delay=1, dimension=10, radius=64)` — correlation
  dimension (Grassberger-Procaccia); attractor dimensionality.
- `fractal_dfa(signal, multifractal=False, q=2)` — detrended fluctuation
  analysis. α ≈ 0.5 uncorrelated, ≈ 1.0 pink/healthy, ≈ 1.5 brown; HRV α1
  (4–11 beats) drops in cardiac pathology.
- `fractal_mfdfa(signal, q=None)` — multifractal DFA → generalized Hurst h(q)
  and spectrum width. `fractal_tmf(signal)` — multifractal nonlinearity.
- `fractal_density(signal)`, `fractal_linelength(signal)` — simple proxies
  (line length is a cheap EEG-seizure feature).

## Nonlinear dynamics — `nk.complexity_*`

- `complexity_lyapunov(signal, delay=None, dimension=None, sampling_rate=1000)`
  — largest Lyapunov exponent (λ > 0 = chaotic divergence).
- `complexity_lempelziv(signal, symbolize='median')` — algorithmic complexity
  (consciousness/anesthesia in EEG).
- `complexity_rqa(signal, delay=1, dimension=3, tolerance='sd')` — recurrence
  quantification: recurrence rate, determinism, laminarity, trapping time,
  longest lines, entropy of line lengths.
- `complexity_hjorth(signal)` — Activity / Mobility / Complexity time-domain
  parameters (EEG features).
- `complexity_decorrelation(signal)` — memory duration (autocorrelation-decay
  lag). `complexity_relativeroughness(signal)` — smoothness.

## Information theory

- `nk.fisher_information(signal, delay=1, dimension=2)` — order measure.
- `nk.fishershannon_information(signal)` — Fisher × Shannon (order-disorder).
- `nk.mutual_information(signal1, signal2, method='knn')` — nonlinear dependence
  (`'knn'`, `'kernel'`, `'binning'`).

## Length requirements

| Measure | Minimum | Optimal |
|---|---|---|
| Shannon entropy | 50 | 200+ |
| ApEn / SampEn | 100–300 | 500–1000 |
| Multiscale entropy | 500 | 1000+ / scale |
| DFA | 500 | 1000+ |
| Lyapunov | 1000 | 5000+ |
| Correlation dimension | 1000 | 5000+ |

## Interpretation caveats

- Complexity is context-dependent — compare within-subject or between groups,
  not against a universal "good" value.
- Maximum entropy ≠ maximum complexity: white noise has high entropy but low
  structured complexity (MSE separates the two).
- Many measures are amplitude- and stationarity-sensitive — z-score, detrend,
  and check stationarity; segment non-stationary signals.

## Key references

- Pincus (1991), *PNAS* 88(6). Approximate entropy.
- Richman & Moorman (2000), *Am. J. Physiol.* 278(6). Sample entropy.
- Costa et al. (2005), *Phys. Rev. E* 71(2). Multiscale entropy.
- Grassberger & Procaccia (1983), *Physica D* 9. Correlation dimension.
