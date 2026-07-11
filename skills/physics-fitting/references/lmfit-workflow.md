# lmfit — bounded fits, constraints, and confidence intervals

`lmfit` wraps scipy's optimizers with named parameters, bounds, fixed values,
algebraic constraints, composite models, and profile-likelihood confidence
intervals. Reach for it whenever a plain `curve_fit` is not expressive enough.

## Model and Parameters

```python
from lmfit import Model

def exponential_decay(t, A, tau, C):
    return A * np.exp(-t / tau) + C

model  = Model(exponential_decay)
params = model.make_params(A=10, tau=3, C=0)   # names inferred from the function

params['A'].min   = 0        # bound below
params['tau'].min = 0.01     # positive-definite lifetime
params['C'].set(min=-1, max=1)
params['C'].vary  = True     # set False to freeze a parameter
```

`weights` in `model.fit` multiply the residual, so pass `1/sigma` to reproduce a
chi-squared fit:

```python
result = model.fit(y, params, t=t, weights=1.0 / sig)
print(result.fit_report())
```

## Reading the result object

| Attribute | Meaning |
|---|---|
| `result.params` | fitted `Parameters`; each has `.value` and `.stderr` |
| `result.best_fit` | model evaluated at the best-fit params, on the input x |
| `result.residual` | weighted residual array |
| `result.chisqr` | chi-squared |
| `result.redchi` | reduced chi-squared (chi-squared / ndof) |
| `result.nfree` | degrees of freedom |
| `result.aic`, `result.bic` | information criteria (lower is better) |
| `result.success`, `result.nfev` | converged? how many function evals |
| `result.covar` | covariance matrix (may be `None` if it failed) |

`result.fit_report()` prints values, standard errors, the reduced chi-squared,
AIC/BIC, and parameter correlations in one block.

## Algebraic constraints between parameters

Tie parameters together with `expr` instead of fitting redundant free
parameters. The constrained parameter is computed, not varied.

```python
params.add('ratio', value=2.0)
params.add('A2', expr='A * ratio')     # A2 is derived, not fit independently
```

## Profile-likelihood confidence intervals

Standard errors from the covariance assume a parabolic likelihood. When that is
a poor approximation, `conf_interval()` maps out the actual likelihood profile
and returns (possibly asymmetric) intervals.

```python
ci = result.conf_interval(sigmas=[1, 2])   # 1- and 2-sigma
result.ci_report()                          # formatted table
# ci[name] -> list of (sigma_level, value) tuples, negative to positive
```

This is slower (it refits at many parameter values) but is the honest interval
for skewed or bounded parameters.

## Built-in and composite models

`lmfit` ships peak/step/background models you can add together. A composite model
sums the components and merges their parameters, so you fit a peak plus a linear
background in one shot.

```python
from lmfit.models import GaussianModel, LinearModel

peak = GaussianModel(prefix='g_')       # params g_amplitude, g_center, g_sigma
bkg  = LinearModel(prefix='b_')         # params b_slope, b_intercept
composite = peak + bkg

params = composite.make_params(
    g_amplitude=5, g_center=0, g_sigma=1, b_slope=0, b_intercept=0)
result = composite.fit(y, params, x=x)
```

Useful built-ins: `GaussianModel`, `LorentzianModel`, `VoigtModel`,
`ExponentialModel`, `PowerLawModel`, `LinearModel`, `PolynomialModel`,
`StepModel`, `ConstantModel`. Many peak models expose `guess()` to seed
parameters from the data:

```python
params = peak.guess(y, x=x)
```

`ExpressionModel('a*exp(-x/b)+c')` builds a model straight from a string when you
do not want to write a function.

## Robust and alternative methods

`method='least_squares'` exposes scipy's TRF optimizer with robust `loss`
options; `method='nelder'` (Nelder-Mead) helps when gradients are unreliable.
Fit once with a robust method to escape a bad basin, then refine with the
default `leastsq`.

## When lmfit reports no errors

If `result.errorbars` is `False` or `stderr` is `None`, the covariance could not
be computed — usually a parameter hit a bound or the problem is degenerate.
Loosen the bound, fix a redundant parameter, or add data, then refit.
