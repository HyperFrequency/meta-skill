# Dimension-Constrained Symbolic Regression

Telling PySR the physical units of your inputs and output is the single most powerful way to
shrink the search space for a physics problem. PySR uses `DynamicQuantities.jl` to propagate
units through candidate expressions and penalizes any expression that is not dimensionally
homogeneous. Dimensionally impossible candidates (adding a length to a time, taking `sin` of a
dimensioned quantity, ...) are pushed out of the population, so the evolver spends its budget
only on physically meaningful forms.

For the theory of which dimensionless groups a problem depends on (Buckingham Pi), see the
sibling skill `dimensional-analysis`. This file is only about wiring units into PySR.

## How to pass units

Units are passed to `.fit`, not the constructor. `X_units` is a list of unit strings (one per
input column); `y_units` is a single string. Set a large penalty on the constructor so the
constraint actually bites:

```python
model = PySRRegressor(
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["square", "sqrt"],
    maxsize=25,
    niterations=100,
    dimensional_constraint_penalty=10 ** 5,   # cost added to loss for a unit violation
)

model.fit(X, y, X_units=["m", "kg", "s"], y_units="m / s^2")
```

### Unit-string syntax

Strings are parsed by DynamicQuantities.jl:

- SI base and derived units by name: `"m"`, `"kg"`, `"s"`, `"K"`, `"A"`, `"mol"`, `"N"`,
  `"J"`, `"Pa"`, `"W"`, `"Hz"`.
- Products, quotients, powers: `"kg * m / s^2"`, `"m^3 / (kg * s^2)"`.
- Physical constants via the `Constants` namespace: `"Constants.M_sun"`, `"Constants.G"`,
  `"Constants.R_earth"`, `"Constants.c"`. Useful when your data is already in astronomical or
  natural units.
- A dimensionless column is `""` or `"1"`.

If you build `X`/`y` with a units library (`astropy.units`, `pint`), convert to plain numeric
arrays in a chosen unit system first, then pass the matching unit strings — PySR works on the
raw numbers plus the unit labels, not on unit-carrying arrays.

## Worked example: Kepler's third law

Recover `T^2 ∝ a^3 / (G M)` from planetary data. Fit `T^2` (units `s^2`) as a function of
semi-major axis `a` (`m`), central mass `M` (`kg`), and the gravitational constant `G`
(`m^3 kg^-1 s^-2`):

```python
import numpy as np
from pysr import PySRRegressor

G = 6.674e-11
M_sun = 1.989e30
a = np.array([57.9, 108.2, 149.6, 227.9, 778.6]) * 1e9      # m
T = np.array([88, 224.7, 365.2, 687, 4331]) * 86400         # s

X = np.column_stack([a, np.full_like(a, M_sun), np.full_like(a, G)])
y = T ** 2

model = PySRRegressor(
    niterations=80,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["cube", "square"],
    maxsize=20,
    dimensional_constraint_penalty=10 ** 5,
)
model.fit(X, y, X_units=["m", "kg", "m^3 / (kg * s^2)"], y_units="s^2")
print(model.sympy())   # expect ~ (4*pi^2) * a^3 / (G * M)
```

With three inputs of these dimensions and a `s^2` output, the only unit-consistent monomial is
`a^3 / (G M)`, so the constraint does most of the work; the evolver just fits the `4π²`
prefactor.

## Interaction with other options

- **`complexity_of_constants`** — dimensional constraints do not fix numeric prefactors. Raise
  `complexity_of_constants` (e.g. to 2) so the search prefers a clean `a^3/(GM)` with one
  constant over a form that hides structure inside several tuned constants.
- **Operators that break dimensions** — `exp`, `log`, `sin`, `cos` require dimensionless
  arguments. If your inputs are dimensioned, either omit these operators or provide a
  dimensionless group as an input column so the transcendental has something valid to act on.
- **Penalty magnitude** — too small and violations survive; `10^4`-`10^6` is a good range.
  If the run finds nothing, temporarily drop the penalty to confirm units are not over-
  constraining a mis-specified problem (e.g. wrong `y_units`).

## When units are unknown

If you do not know all units but know the problem is scale-free, feed **dimensionless groups**
as inputs instead (compute them with `dimensional-analysis`) and leave `X_units`/`y_units`
unset. This is often cleaner than partial unit annotation.
