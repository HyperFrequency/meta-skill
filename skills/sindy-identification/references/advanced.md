# SINDy: Advanced Variants and Failure Modes

Extensions beyond the basic ODE-from-clean-data workflow, plus a diagnostics
table. These variants change the library or optimizer; the fit/simulate/inspect
loop stays the same.

## Weak / integral formulation (noise robustness)

Numerically differentiating noisy data is the biggest source of SINDy error. The
**weak formulation** avoids pointwise derivatives by integrating the governing
equation against smooth test functions over subdomains, so noise averages out.
In PySINDy this is exposed through weak-form libraries (`ps.WeakPDELibrary` for
spatial problems; the ODE weak form is configured through the same library
family with spatial terms disabled). Prefer this over `SmoothedFiniteDifference`
when noise is substantial and you have enough samples to define integration
windows.

## PDE discovery (PDE-FIND)

Standard SINDy discovers ODEs. To discover a PDE
`u_t = f(u, u_x, u_xx, …)` from spatiotemporal field data, use `ps.PDELibrary`
(or `ps.WeakPDELibrary` for the noise-robust weak form). These libraries build
candidate terms that include spatial derivatives computed on a grid, and the
data array carries spatial as well as temporal axes. This is a distinct workflow
from the basic skill — reach for it only when your data is a field `u(x, t)`,
not a low-dimensional trajectory.

## Ensembling (uncertainty and robustness)

Wrap any optimizer in `ps.EnsembleOptimizer` to bag over subsamples of the data
rows ("bagging") and/or library columns ("library ensembling"). Fitting many
sub-models yields a distribution over each coefficient; keeping only terms that
appear consistently across the ensemble sharply reduces false positives on noisy
data. Inspect `optimizer.coef_list` for the per-ensemble coefficient sets.

## Constrained and stability-promoting fits

- `ps.ConstrainedSR3` — impose linear equality/inequality constraints on
  coefficients to bake in known conservation laws or symmetries (requires
  `cvxpy`).
- `ps.TrappingSR3` — promote globally bounded (Lyapunov-stable) models for
  quadratically-nonlinear systems such as fluid Galerkin models; prevents the
  finite-time blow-up that unconstrained fits can produce.

## Discrete-time maps

Set `discrete_time=True` on `ps.SINDy` to identify a map `x_{k+1} = f(x_k)`
instead of a continuous ODE — appropriate for data that is inherently a
discrete iteration (e.g. a logistic map) rather than a sampled flow.

## Failure modes and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Too many terms discovered | Threshold too low / overfitting noise | Raise `STLSQ.threshold`; consider ensembling |
| Known term missing | Threshold too high, or term absent from library | Lower threshold; verify the library contains the term |
| Poor simulation accuracy despite good `score` | Noisy derivative estimates | Use `SmoothedFiniteDifference`, `SINDyDerivative`, or the weak form |
| `simulate` diverges / returns NaN | Discovered model dynamically unstable | Check coefficient signs; try `TrappingSR3` or add data; treat as disqualifying in a sweep |
| Coefficients look right but slightly off | Timestep or units mismatch | Confirm `t`/`dt` is in the same time units as intended for `dx/dt` |
| `ValueError` on `fit` about shape | `x` passed as `(n_features, n_samples)` | Transpose to `(n_samples, n_features)` |
| Discovery unstable run-to-run | Too little data / too rich a library | More/longer trajectories, lower polynomial degree, or `multiple_trajectories=True` |
| Nothing survives thresholding | Threshold above all coefficient magnitudes | Lower threshold; rescale/normalize state variables |

## Practical guidance

1. Start with `PolynomialLibrary(degree=2)` — most classical physics ODEs are
   low-order polynomial.
2. Treat threshold tuning as the core task; always sweep, never guess (see
   `references/workflows.md`).
3. Denoise before differentiating; derivative noise dominates SINDy error.
4. A library that lacks the true term guarantees failure — design it
   deliberately.
5. Validate by forward simulation, not just the derivative-fit `score`.
6. Normalize/scale state variables of very different magnitudes so a single
   threshold applies fairly across equations.
