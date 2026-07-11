# Error propagation to derived quantities

Fit parameters are rarely the final answer — you usually compute something from
them (a half-life from a rate, a ratio, an integral, a value at a specific x).
The uncertainty on that derived quantity must include the parameter
**correlations**, not just their individual errors.

## The Jacobian rule

For a function `g(p)` of the fitted parameters `p` with covariance matrix `Σ`
(the `pcov` from `curve_fit` or `result.covar` from lmfit), the first-order
propagated covariance is:

```
Σ_g = J Σ J^T
```

where `J` is the Jacobian of `g` with respect to `p`, evaluated at the best-fit
parameters. For a scalar `g`, `sigma_g = sqrt(J Σ J^T)`. Add-in-quadrature is the
special case where `Σ` is diagonal (no correlations) — using it when parameters
are correlated gives a wrong (often too small) error.

## Linear derived quantity

If `g` is linear in one parameter, propagation is trivial and exact:

```python
half_life  = popt[1] * np.log(2)     # t_1/2 = tau * ln 2
d_halflife = perr[1] * np.log(2)     # exact: constant factor on a single param
```

## General numerical Jacobian

For nonlinear `g` or several correlated parameters, compute `J` by central
finite differences and apply the rule. Central differences are more accurate than
the one-sided version.

```python
import numpy as np

def propagate(g, p, cov, rel_step=1e-6):
    """Propagate covariance `cov` of params `p` through vector/scalar g(p)."""
    p  = np.asarray(p, float)
    f0 = np.atleast_1d(g(p))
    J  = np.zeros((f0.size, p.size))
    for i in range(p.size):
        h  = rel_step * max(abs(p[i]), 1.0)      # scale the step to the value
        pp, pm = p.copy(), p.copy()
        pp[i] += h; pm[i] -= h
        J[:, i] = (np.atleast_1d(g(pp)) - np.atleast_1d(g(pm))) / (2 * h)
    cov_g = J @ cov @ J.T
    return f0, np.sqrt(np.diag(cov_g))

# Example: value of the decay curve at t = 4, with correlated A, tau, C
def y_at_4(p):
    A, tau, C = p
    return A * np.exp(-4.0 / tau) + C

val, err = propagate(y_at_4, popt, pcov)
print(f"y(4) = {val[0]:.3f} +/- {err[0]:.3f}")
```

Notes:
- Scale the finite-difference step to each parameter's magnitude (as above) so it
  stays meaningful whether the parameter is 1e-9 or 1e6.
- The result is first-order (linearized). If `g` is strongly nonlinear over the
  parameter's uncertainty range, prefer a Monte Carlo propagation: sample `p ~
  MVN(popt, pcov)`, evaluate `g` on each draw, and take the spread.

## Monte Carlo alternative

More robust for strongly nonlinear `g`, and it gives the full distribution, not
just a standard deviation:

```python
rng     = np.random.default_rng(0)
draws   = rng.multivariate_normal(popt, pcov, size=100_000)
g_draws = np.array([y_at_4(p) for p in draws])
print(np.mean(g_draws), np.std(g_draws),
      np.percentile(g_draws, [2.5, 97.5]))
```

## The `uncertainties` package

For algebraic expressions, the third-party `uncertainties` package (BSD)
propagates correlated errors automatically through normal Python arithmetic and
numpy-like functions, so you do not hand-write a Jacobian:

```python
from uncertainties import correlated_values
import uncertainties.unumpy as unp
A, tau, C = correlated_values(popt, pcov)   # carries covariance
t_half    = tau * unp.log(2)                # error propagated automatically
print(t_half)                               # value +/- error
```

Prefer `correlated_values` (which ingests the full covariance) over creating each
variable independently, which would drop the correlations.
