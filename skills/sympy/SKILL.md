---
name: sympy
version: 0.1.0
description: >-
  Symbolic mathematics in Python with SymPy — exact computation over
  mathematical symbols instead of floating-point approximations. Use when you
  need to solve equations algebraically (algebraic systems, ODEs), do calculus
  (derivatives, integrals, limits, series), simplify or manipulate
  algebraic/trigonometric expressions, work with symbolic matrices and linear
  algebra, or handle physics (mechanics, quantum, units), number theory,
  geometry, combinatorics, logic/sets, or symbolic statistics — and when you
  want exact results like sqrt(2) or Rational(1, 3) rather than 1.414... Also use
  to turn a derived formula into fast numerical code (lambdify, codegen,
  ufuncify) or LaTeX/MathML output. Do NOT use for purely numerical work: fit
  statistical models with statsmodels, ML with scikit-learn, plot with
  matplotlib, and crunch large arrays with NumPy/SciPy directly (lambdify the
  symbolic result first). This file is a router; deep API detail lives in
  references/.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: BSD-3-Clause (SymPy)
---

# SymPy

## Overview

SymPy is Python's computer algebra system: it computes with mathematical
*symbols* and keeps results exact (`sqrt(2)`, `pi`, `Rational(1, 3)`) instead of
collapsing them to floats. Reach for it whenever the answer should be a formula,
an exact number, or a manipulated expression — not a numerical approximation.

This SKILL.md is a lean router. Orienting snippets live here; deep API detail,
extended examples, and per-domain workflows live in `references/`.

## Installation

```bash
uv pip install sympy
# Common companions for numeric evaluation and plotting:
uv pip install numpy scipy matplotlib
```

## When to Use This Skill

Use this skill when you need to:

- Solve equations exactly — algebraic (`solveset`, `solve`), linear systems
  (`linsolve`), nonlinear systems (`nonlinsolve`), or ODEs (`dsolve`).
- Do calculus — derivatives, indefinite/definite/improper integrals, limits,
  Taylor/Laurent series.
- Simplify or transform expressions — `simplify`, `expand`, `factor`, `cancel`,
  `collect`, `trigsimp`, `apart`, `together`.
- Work with **symbolic** matrices — determinants, inverses, eigenvalues,
  decompositions, nullspace/rank with symbolic entries.
- Compute in a math domain — physics (mechanics, quantum, units), number theory,
  geometry, combinatorics, logic/sets, polynomials, special functions, symbolic
  probability.
- Get an exact value (`sqrt(8) + pi`) or arbitrary-precision numeric one
  (`.evalf(50)`).
- Convert a derived formula into executable code (`lambdify`, `codegen`,
  `ufuncify`) or typeset output (`latex`, `mathml`, `pprint`).

## When NOT to Use This Skill

Reach for a different tool when:

- You want **numeric** answers on real data at scale — use NumPy/SciPy directly.
  Derive the formula in SymPy, then `lambdify` it into a fast callable.
- You are fitting statistical models or doing inference — use `statsmodels`
  (regression/econometrics/time series) or `pymc` (Bayesian).
- You are doing machine learning — use `scikit-learn` (or deep-learning skills).
- You are plotting — use `matplotlib`; SymPy's own plotting is a thin wrapper.
- You are analyzing graphs/networks numerically — use `networkx`.
- The problem has no closed form — SymPy may hang or return the input unevaluated.
  Fall back to `nsolve`, numerical integration, or SciPy.

## Core Capabilities

### 1. Symbols, assumptions, and exact arithmetic

Define symbols before use, and give them assumptions so SymPy can simplify
correctly. Use `Rational`/`S` (not Python floats) to stay exact.

```python
from sympy import symbols, Rational, S, sqrt
x, y = symbols('x y')
a = symbols('a', positive=True, real=True)
n = symbols('n', integer=True)

sqrt(a**2)          # a  (thanks to positive=True; otherwise Abs(a))
Rational(1, 2) * x  # exact 1/2 * x  (0.5 * x would be a float approximation)
```

Substitute with `.subs()`, evaluate numerically with `.evalf(precision)`.
See `references/core.md` for the assumptions system, substitution, and pitfalls.

### 2. Simplification and manipulation

```python
from sympy import simplify, expand, factor, cancel, trigsimp
simplify(sin(x)**2 + cos(x)**2)     # 1
expand((x + 1)**3)                  # x**3 + 3*x**2 + 3*x + 1
factor(x**2 - 1)                    # (x - 1)*(x + 1)
```

`simplify` is a heuristic catch-all; targeted functions (`factor`, `trigsimp`,
`powsimp`, `logcombine`, `radsimp`) are faster and more predictable. Full menu
in `references/core.md`.

### 3. Calculus

```python
from sympy import diff, integrate, limit, series, oo, exp, sin
diff(x**2 * y**3, x, y)             # 6*x*y**2  (mixed partial)
integrate(exp(-x), (x, 0, oo))      # 1         (improper, definite)
limit(sin(x)/x, x, 0)               # 1
series(exp(x), x, 0, 5)             # 1 + x + x**2/2 + x**3/6 + x**4/24 + O(x**5)
```

Use `limit()` (not `.subs()`) at singularities. Indefinite integrals omit the
`+ C`. Details and one-sided limits in `references/core.md`.

### 4. Equation solving

Pick the right solver:

| Problem | Function |
| --- | --- |
| Single algebraic equation | `solveset(eq, x, domain=S.Reals)` |
| General / transcendental (list output) | `solve(eq, x)` |
| Linear system | `linsolve([...], x, y)` |
| Nonlinear system | `nonlinsolve([...], x, y)` |
| ODE | `dsolve(ode, f(x), ics={...})` |
| No closed form (numeric root) | `nsolve(eq, x, guess)` |

```python
from sympy import solveset, Eq, S
solveset(x**2 - 4, x)               # {-2, 2}
solveset(x**2 + 1, x, domain=S.Reals)  # EmptySet
```

Solver selection, return types, and worked ODE examples in `references/core.md`.

### 5. Matrices and linear algebra

`Matrix(...)`, `.det()`, `.inv()`/`M**-1`, `.eigenvals()`, `.eigenvects()`,
`.diagonalize()`, `.rref()`, `.nullspace()`, plus LU/QR/Cholesky/SVD and
solving `A x = b` (`A.solve(b)`, `A.solve_least_squares(b)`). Everything works
with symbolic entries. See `references/linear-algebra.md`.

### 6. Physics and mechanics

Vector algebra in reference frames, Lagrangian and Kane's-method dynamics,
rigid bodies and joints, quantum states/operators/gates, and dimensional
`sympy.physics.units`. See `references/physics.md`.

### 7. Advanced mathematics

Analytic geometry (2D/3D), number theory (primes, factorization, modular
arithmetic, Diophantine equations), combinatorics and permutation groups,
Boolean logic and set theory, polynomials and Gröbner bases, symbolic
probability (`sympy.stats`), and special functions. See `references/advanced.md`.

### 8. Code generation and output

Turn expressions into fast callables and typeset math:

```python
from sympy import lambdify
import numpy as np
f = lambdify(x, x**2 + 2*x + 1, 'numpy')   # vectorized NumPy function
f(np.arange(1000))                          # far faster than subs()+evalf() in a loop
```

Also `codegen` (C/Fortran), `autowrap`/`ufuncify` (compiled), `latex`, `mathml`,
`pprint`, `cse` (common-subexpression elimination), and parsers
(`parse_expr`, `parse_latex`). See `references/codegen-and-printing.md`.

## Best Practices

- **Define symbols first, with assumptions.** Assumptions (`real`, `positive`,
  `integer`, ...) drive correct simplification.
- **Stay exact.** Use `Rational(1, 2)` or `S(1)/2`, never `0.5`, inside symbolic
  expressions. Call `.evalf()` only at the end when you want a number.
- **Vectorize with `lambdify`.** Never loop `expr.subs(...).evalf()` over many
  values; build one numeric function instead.
- **Prefer targeted simplifiers** over `simplify` for speed and predictability.
- **Verify solutions** by substituting back:
  `simplify(eq.subs(x, sol)) == 0`.

## Common Pitfalls

- `NameError: name 'x' is not defined` — you forgot `x = symbols('x')`.
- Approximate/ugly results — a Python float (`0.5`, `2.0`) leaked into the
  expression; use `Rational`/`S`.
- Solver returns nothing or hangs — no closed form; try another solver, add
  assumptions, restrict the `domain`, or drop to `nsolve`.
- Simplification "does nothing" — try a targeted function, add assumptions, or
  `simplify(expr, force=True)` (aggressive, can be unsound without assumptions).

Extended troubleshooting lives in `references/core.md`.

## Reference Files

- `references/core.md` — symbols, assumptions, arithmetic, simplification,
  calculus, equation/ODE solving, troubleshooting.
- `references/linear-algebra.md` — matrix construction, operations, eigen-
  problems, decompositions, linear systems, sparse/symbolic matrices.
- `references/physics.md` — vectors, classical/Lagrangian/Kane mechanics,
  quantum, units and dimensional analysis.
- `references/advanced.md` — geometry, number theory, combinatorics, logic/sets,
  polynomials, `sympy.stats`, special functions.
- `references/codegen-and-printing.md` — lambdify, codegen, autowrap/ufuncify,
  LaTeX/MathML/pretty printing, parsing, high-precision numerics, `cse`.

## Additional Resources

- Documentation: https://docs.sympy.org/
- Tutorial: https://docs.sympy.org/latest/tutorials/intro-tutorial/index.html
- API reference: https://docs.sympy.org/latest/reference/index.html
