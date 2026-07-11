# Error Analysis, Equilibration & Troubleshooting

Monte Carlo samples are correlated, so the hard part is not the mean — it's an
honest error bar. This is where most simulations quietly lie to you.

## Integrated autocorrelation time

Successive Markov-chain samples are correlated. The variance of the mean is not
`σ²/N` but `σ²·(2τ)/N`, where `τ` is the integrated autocorrelation time. Ignore
it and your error bars are too small by a factor of `√(2τ)` — near `T_c` (with
Metropolis) `τ` can be hundreds.

```python
import numpy as np


def autocorrelation_time(data):
    """Integrated autocorrelation time τ from the normalized ACF."""
    data = np.asarray(data, dtype=float)
    n = len(data)
    data = data - data.mean()
    var = data.var()
    if var == 0:
        return 0.5

    acf = np.correlate(data, data, mode="full")[n - 1:]
    acf = acf / acf[0]

    tau = 0.5
    for k in range(1, n // 4):          # self-consistent / automatic windowing
        if acf[k] < 0:                  # truncate at first sign change
            break
        tau += acf[k]
    return tau


def corrected_error(data):
    """Standard error of the mean, corrected for autocorrelation."""
    data = np.asarray(data, dtype=float)
    tau = autocorrelation_time(data)
    n_eff = len(data) / (2 * tau)       # effective independent samples
    return data.std() / np.sqrt(n_eff), tau
```

- **Effective sample size:** `N_eff = N / (2τ)`.
- **Corrected error:** `SE = σ · √(2τ / N)`.
- The naive `*_std` returned by `simulate()` uses `τ = 0.5` (uncorrelated)
  implicitly — always recompute the error with `corrected_error` for anything
  you report.

## Jackknife / blocking for derived quantities

`C` and `χ` are *nonlinear* functions of samples (variances), so their error
does not follow from simple propagation. Use blocking or jackknife:

- **Blocking:** split the chain into `B` contiguous blocks each much longer than
  `τ`, compute the observable per block, take the standard error over blocks.
- **Jackknife:** recompute the observable `N` times, each leaving one block out;
  the jackknife variance gives the error and removes leading-order bias.

The `statistical-analysis` skill has ready resampling routines if you'd rather
not hand-roll these.

## Equilibration diagnostics

- **Discard enough burn-in.** Plot an observable (energy or `|M|`) vs sweep index
  and discard everything before it plateaus. `τ` sets the scale: burn in for
  many multiples of `τ`.
- **Two starts.** Run one chain from a hot (random) start and one from a cold
  (all-aligned) start. They must converge to the same plateau; if they don't,
  you haven't equilibrated (or you're seeing metastability / a first-order
  transition).
- **Near `T_c`, τ explodes** for Metropolis (critical slowing down,
  `τ ~ L^z` with `z ≈ 2.17` in 2D). This is precisely when to switch to the
  Wolff cluster algorithm (`algorithms.md`), which drives `z` toward ~0.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Equilibration takes forever near `T_c` | Critical slowing down of Metropolis | Switch to the Wolff cluster algorithm |
| Very noisy `C`/`χ` | Too few effective samples / long `τ` | Increase `n_measure`; block or jackknife; use Wolff |
| Estimated `T_c` off from 2.269 | Finite-size shift (real) or a bug | Run larger `L` and finite-size scaling; use the Binder crossing |
| `⟨M⟩ ≈ 0` even in the ordered phase | Measuring signed `M`, which averages out by symmetry | Measure `⟨|M|⟩` |
| Error bars look implausibly tight | Autocorrelation ignored | Recompute with `corrected_error` / jackknife |
| Hot and cold starts disagree | Not equilibrated, or metastability | Extend burn-in; check for a first-order transition |
| Specific-heat peak barely grows with `L` | Correct — 2D Ising `C` diverges only logarithmically (`α = 0`) | Not a bug; use `χ` (`L^{7/4}`) to test scaling instead |
| Wolff gives wrong physics with a field | Cluster construction assumes zero/simple field | Use Metropolis when an external field is present |
