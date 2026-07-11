# PySINDy API Reference

Capability-level reference for the pieces you assemble into a `ps.SINDy` model.
Exact signatures evolve across PySINDy releases (this targets the 1.7+ / 2.x
line); confirm defaults with `help(ps.SINDy)` and the installed version's docs
if a specific value is load-bearing.

## The estimator: `ps.SINDy`

`ps.SINDy` follows the scikit-learn estimator convention.

Constructor arguments (all optional):

| Argument | Purpose |
|---|---|
| `feature_library` | The candidate-term library Θ (default `PolynomialLibrary(degree=2)`). |
| `optimizer` | The sparse-regression solver (default `STLSQ`). |
| `differentiation_method` | How `dx/dt` is estimated from `x` (default finite difference). |
| `feature_names` | List of state-variable names used when printing equations. |
| `discrete_time` | If `True`, fits a map `x_{k+1} = f(x_k)` instead of a continuous ODE. |

Core methods:

- `model.fit(x, t=..., x_dot=None, u=None, multiple_trajectories=False)` — fit
  the model. `x` must be shape `(n_samples, n_features)`. `t` is either a scalar
  timestep or a 1-D array of timestamps. Pass `x_dot` to supply your own
  precomputed derivatives (skips numerical differentiation). Pass `u` for
  control/forcing inputs (SINDy-with-control). Set `multiple_trajectories=True`
  and pass a list of arrays to fit across several runs.
- `model.print(lhs=None, precision=3)` — pretty-print the discovered equations.
- `model.simulate(x0, t, u=None)` — integrate the discovered ODE forward from
  initial condition `x0` over time grid `t`. Returns the simulated trajectory.
- `model.predict(x, u=None)` — evaluate `f(x)` (the right-hand side) at given
  states without integrating.
- `model.score(x, t=..., x_dot=None, u=None, metric=...)` — goodness-of-fit
  (R² by default) of the derivative prediction.
- `model.coefficients()` — the coefficient matrix Ξ, shape
  `(n_features, n_library_terms)`; rows are equations, columns are library terms.
- `model.get_feature_names()` — ordered names of the library columns.
- `model.complexity` — number of nonzero coefficients (model "size").
- `model.equations(precision=3)` — equations as a list of strings.

## Optimizers (the sparse solver)

Chosen via the `optimizer=` argument. This is where sparsity is enforced.

| Optimizer | Character |
|---|---|
| `ps.STLSQ(threshold, alpha, max_iter)` | Sequentially-thresholded least squares. The default and the original SINDy solver. `threshold` zeros coefficients below it each iteration; `alpha` is ridge (L2) regularization. Start here. |
| `ps.SR3(threshold, thresholder, nu)` | Sparse Relaxed Regularized Regression. Supports `"l0"`, `"l1"`, `"cad"` thresholders; often more robust than STLSQ. |
| `ps.ConstrainedSR3(...)` | SR3 with linear equality/inequality constraints on coefficients (e.g. enforce energy conservation or known symmetries). Needs `cvxpy`. |
| `ps.TrappingSR3(...)` | Enforces global boundedness/stability for fluid-like quadratic systems. |
| `ps.SSR(alpha)` | Stepwise Sparse Regression — greedily removes one term at a time. |
| `ps.FROLS()` | Forward Regression Orthogonal Least Squares — greedy forward selection. |
| `ps.MIOSR(target_sparsity)` | Mixed-Integer Optimized Sparse Regression — exact cardinality control via a solver. Needs the `miosr`/`gurobi` extra. |
| `ps.EnsembleOptimizer(opt, ...)` | Wraps any optimizer to bag over data/library subsamples, giving coefficient distributions and robustness. See `references/advanced.md`. |

`threshold` (STLSQ/SR3) is the primary sparsity knob. `alpha` trades bias for
variance. `max_iter` bounds the thresholding iterations.

## Feature libraries (candidate terms Θ)

Chosen via `feature_library=`. Libraries can be **added** (`+`, concatenates
terms) or **multiplied via tensor** (element-wise products) using
`ps.GeneralizedLibrary`.

| Library | Terms produced |
|---|---|
| `ps.PolynomialLibrary(degree=n, include_bias=True, include_interaction=True)` | All monomials up to total degree `n`, including cross terms like `x*y`. Degree 2 covers most classical mechanics/physics ODEs. |
| `ps.FourierLibrary(n_frequencies=k)` | `sin(mx)`, `cos(mx)` for `m = 1..k`. For oscillatory / periodic systems. |
| `ps.CustomLibrary(library_functions, function_names)` | Arbitrary user callables (e.g. `lambda x: np.exp(x)`) with matching name-formatters. |
| `ps.IdentityLibrary()` | Passes features through unchanged (use when `x` already holds engineered features). |
| `ps.GeneralizedLibrary([lib1, lib2], ...)` | Combine multiple libraries, optionally applying different libraries to different input variables. |
| `ps.PDELibrary(...)`, `ps.WeakPDELibrary(...)` | Spatial-derivative terms for PDE discovery. See `references/advanced.md`. |

If the true governing term is not representable by the library, SINDy cannot
recover it — library design is a modeling decision, not a formality.

## Differentiation methods

Chosen via `differentiation_method=`. Only matters when you let SINDy compute
`dx/dt` (i.e. you did not pass `x_dot`). Noise in derivatives is the dominant
failure source, so this matters for real data.

| Method | Use when |
|---|---|
| `ps.FiniteDifference(order=2)` | Default. Clean, densely-sampled data. |
| `ps.SmoothedFiniteDifference()` | Noisy data — applies a smoother (Savitzky-Golay by default) before differencing. |
| `ps.SINDyDerivative(kind=...)` | Wraps the `derivative` package (total-variation regularized, spectral, spline, kalman, etc.) for heavier denoising. |

## Key parameter cheat-sheet

| Parameter | Typical default | Effect |
|---|---|---|
| `STLSQ.threshold` | 0.1 | Sparsity cutoff. Raise to drop terms, lower to keep more. The main knob. |
| `STLSQ.alpha` | 0.05 | Ridge (L2) strength; stabilizes the least-squares step. |
| `STLSQ.max_iter` | 20 | Max thresholding iterations. |
| `PolynomialLibrary.degree` | 2 | Highest monomial degree in the library. |
| `FourierLibrary.n_frequencies` | 1 | Number of sine/cosine harmonics. |
