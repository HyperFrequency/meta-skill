# Buckingham Pi Theorem — full method and code

The Buckingham Pi theorem: a physically meaningful relation among `n` variables that involves
`k` independent fundamental dimensions can be rewritten as a relation among `n − k`
independent **dimensionless** groups `Π₁, …, Π_{n−k}`. Here `k` is the rank of the dimension
matrix (usually, but not always, the number of fundamental dimensions present).

## The dimension matrix and its null space

Represent each variable by its exponent vector over the fundamental dimensions. Stack them
column-wise into the **dimension matrix** `D` (rows = dimensions M, L, T, …; columns =
variables). A product `∏ variableⱼ^{cⱼ}` is dimensionless iff `D · c = 0` — i.e. the exponent
vector `c` lies in the **null space of `D`**. A basis of that null space is a complete set of
independent Pi groups.

Use **exact rational arithmetic** for the null space (SymPy), never a floating-point SVD:
Pi-group exponents are rationals like `1, -2, 1/2`, and rounding turns them into noise.

```python
import numpy as np
from sympy import Matrix, Rational, nsimplify


def buckingham_pi(variables, dimensions, verbose=True):
    """Find a basis of dimensionless Pi groups.

    Args:
        variables:  dict {name: {dim: exponent}}, e.g. {'v': {'L': 1, 'T': -1}}
        dimensions: ordered list of fundamental dimensions, e.g. ['M', 'L', 'T']

    Returns:
        list of sympy nullspace vectors; component j is the exponent of variables[j]
        in that Pi group.
    """
    names = list(variables)
    D = Matrix([[Rational(variables[v].get(d, 0)) for v in names] for d in dimensions])

    rank = D.rank()
    n_pi = len(names) - rank

    if verbose:
        print(f"variables={len(names)}  dimensions={len(dimensions)}  rank={rank}")
        print(f"independent Pi groups = {n_pi}")
        header = "      " + " ".join(f"{v:>6}" for v in names)
        print(header)
        for i, d in enumerate(dimensions):
            print(f"  {d:>2}  " + " ".join(f"{int(D[i, j]):>6}" for j in range(len(names))))

    null = D.nullspace()  # exact basis of the null space
    for k, vec in enumerate(null, 1):
        terms = [f"{names[j]}^{vec[j]}" for j in range(len(names)) if vec[j] != 0]
        print(f"  Π{k} = " + " · ".join(terms))
    return null
```

### Worked example — drag on a sphere

```python
variables = {
    'F':   {'M': 1, 'L': 1, 'T': -2},   # drag force
    'v':   {'L': 1, 'T': -1},           # free-stream velocity
    'd':   {'L': 1},                    # diameter
    'rho': {'M': 1, 'L': -3},           # fluid density
    'mu':  {'M': 1, 'L': -1, 'T': -1},  # dynamic viscosity
}
buckingham_pi(variables, ['M', 'L', 'T'])
# rank = 3, so 5 - 3 = 2 Pi groups. A convenient basis:
#   Π1 = F / (rho v^2 d^2)   -> drag coefficient C_D
#   Π2 = rho v d / mu        -> Reynolds number Re
# Physical content:  C_D = f(Re).
```

The raw `nullspace()` basis may not be the textbook groups (see below); it is *a* valid basis.

## Getting the conventional named groups (repeating variables)

The null space fixes the groups only up to an invertible change of basis, so `Π₁' = Π₁·Π₂`
is as legitimate as `Π₁`. To recover the *named* groups (Re, C_D, …), use the classical
**repeating-variables** construction:

1. Choose `k = rank(D)` **repeating variables** that (a) together span all the fundamental
   dimensions and (b) are dimensionally independent (their sub-dimension-matrix is full rank).
   Good repeaters are a length, a velocity/density, and a viscosity/force scale.
   Do **not** pick the variable you are solving for (e.g. keep `F` out of the repeaters so it
   appears in exactly one group).
2. Form one Pi group per **non-repeating** variable: multiply that variable by unknown powers
   of the repeaters and solve the small linear system that makes the product dimensionless.

```python
from sympy import symbols, linsolve, Matrix, Rational

def pi_group(target, repeaters, variables, dimensions):
    """Build the single dimensionless group containing `target`, using `repeaters`."""
    a = symbols(f'a0:{len(repeaters)}')  # unknown exponents on the repeating variables
    # exponent of each fundamental dimension in target * prod(repeater_i ** a_i) must be 0
    eqs = []
    for d in dimensions:
        expr = Rational(variables[target].get(d, 0))
        for ai, r in zip(a, repeaters):
            expr += ai * Rational(variables[r].get(d, 0))
        eqs.append(expr)
    sol = list(linsolve(eqs, a))[0]
    powers = {r: p for r, p in zip(repeaters, sol)}
    powers[target] = Rational(1)
    return powers   # e.g. {'F': 1, 'rho': -1, 'v': -2, 'd': -2}  ->  F/(rho v^2 d^2)

# repeaters = ['rho', 'v', 'd']  (span M,L,T and independent)
# pi_group('F',  ['rho','v','d'], variables, ['M','L','T'])  -> C_D
# pi_group('mu', ['rho','v','d'], variables, ['M','L','T'])  -> Re^{-1}  (invert to taste)
```

## Degenerate and edge cases

- **Rank < number of dimensions.** Some dimensions may not appear independently (e.g. M and L
  only ever occur as M·L in your variable set). Then `k = rank(D) < len(dimensions)` and the
  Pi count is `n − rank`, not `n − #dimensions`. `buckingham_pi` uses the rank, so it is
  correct automatically — but read the printed rank and sanity-check it.
- **Repeaters not independent.** If your chosen repeating variables are dimensionally
  dependent, the linear system in `pi_group` is singular (no unique solution). Pick a
  different set — verify independence by checking the repeaters' sub-matrix has full rank `k`.
- **Zero Pi groups (`n = rank`).** No dimensionless combination exists; the only consistent
  relation is that the variables are dimensionally incompatible — recheck whether a variable
  or a fundamental dimension is missing.
- **Dimensional constants matter.** If gravity `g`, the speed of light `c`, or `k_B` enters
  the physics, include it as a variable — omitting a dimensional constant is the most common
  way to get the wrong Pi count.
- **Angles / counts.** Plane angle, solid angle, and pure counts are already dimensionless;
  do not assign them a fundamental dimension or they will spuriously raise the rank.

## Checklist

1. List every physically relevant variable **and dimensional constant**.
2. Write each one's exponent vector over M, L, T, Θ, I, N, J.
3. Compute `rank(D)` and expect `n − rank` groups.
4. Build a basis via `nullspace()`, or the named groups via repeating variables.
5. Cross-check against known groups for the problem class (Re, Ma, …). A mismatch means a
   missing/extra variable, not a broken theorem.
