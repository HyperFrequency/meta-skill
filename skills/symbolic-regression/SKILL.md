---
name: symbolic-regression
version: 0.1.0
description: >-
  Discover closed-form symbolic equations from data with PySR, an evolutionary
  (genetic-programming) symbolic-regression engine on a Julia backend that returns a Pareto
  front trading accuracy against expression complexity. Use when you want an interpretable
  formula instead of a black-box model — recovering a governing law from experimental data,
  replacing a fitted network with a compact equation, or enforcing physical-dimension
  constraints on the search via `X_units`/`y_units`. Handles custom operators,
  nested-operator constraints, multi-output targets, and built-in feature selection for
  moderate dimensionality. NOT for cases where you already know the functional form and only
  need to fit coefficients (use `physics-fitting`), for identifying the differential
  equations of a dynamical system from time series (use `sindy-identification`), for finding
  conserved quantities (use `conservation-law-discovery`), or for high-dimensional black-box
  prediction where interpretability does not matter.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (PySR / SymbolicRegression.jl)"
---

# Symbolic Regression

## Overview

PySR searches the space of mathematical expressions with a multi-population evolutionary
algorithm (genetic programming) running on a Julia backend (`SymbolicRegression.jl`). Rather
than a single model it returns a **Pareto front**: for each level of complexity, the most
accurate expression found. You pick the point on that front where accuracy stops improving
enough to justify another term — that elbow is usually the real law.

The search is defined by three things you control:

1. **Operators** it may compose — binary (`+ - * /`, `^`) and unary (`sin`, `cos`, `exp`,
   `log`, `sqrt`, `square`, ...).
2. **Complexity budget** — `maxsize` (max nodes in the expression tree) and `parsimony`
   (per-node penalty). Physical laws are usually small; keep this tight.
3. **Constraints** — optional dimensional units, forbidden operator nestings, and
   per-operator argument-size limits that prune physically meaningless candidates.

Everything else is tuning. Start with only `+ - * /`, add a unary operator when you have a
reason (periodicity → `sin`; growth/decay → `exp`), and read the Pareto front, not the last
row of the table.

## When to Use This Skill

- Recovering a governing equation or empirical law from experimental / simulated data.
- Distilling a black-box regressor into a compact, human-readable formula.
- Constraining an equation search by physical dimensions (Buckingham-Pi-style) so only
  unit-consistent expressions survive — see `dimensional-analysis` for the theory.
- Multi-output problems where each target gets its own closed form (e.g. force components).
- Sanity-checking a theoretical prediction against what the data actually implies.

## When NOT to Use This Skill

- You already know the functional form and only need coefficients → use `physics-fitting`
  (nonlinear least squares with uncertainties). Symbolic regression is far more expensive.
- You want the differential equations of a dynamical system from a trajectory → use
  `sindy-identification` (sparse regression on a derivative library); see also
  `dynamical-systems`.
- You want invariants / conserved quantities of a flow → use `conservation-law-discovery`.
- High-dimensional (many tens of raw inputs) black-box prediction where you do not need an
  equation → use a gradient-boosted or neural model. PySR tolerates moderate dimensionality
  via `select_k_features` but is not a general-purpose high-dim learner.

## Installation

```bash
pip install pysr
```

Julia and the backend packages install automatically on the first `import pysr` (about 1-2
minutes, once). Current versions manage their own Julia dependencies through `juliacall`;
there is **no** separate `pysr.install()` step — do not call it. Pin the PySR version in your
environment for reproducibility. See [references/api-reference.md](references/api-reference.md)
for environment and backend-tuning notes.

## Core workflow

```python
import numpy as np
from pysr import PySRRegressor

rng = np.random.default_rng(0)
X = rng.standard_normal((200, 2))          # two input variables, columns x0, x1
y = 2.5 * np.sin(X[:, 0]) + X[:, 1] ** 2   # the (unknown-to-PySR) true law
y += 0.05 * rng.standard_normal(200)       # measurement noise

model = PySRRegressor(
    niterations=60,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["sin", "cos", "exp", "square", "sqrt"],
    maxsize=25,          # complexity ceiling (tree nodes)
    parsimony=0.0032,    # per-node complexity penalty
    populations=15,
    progress=True,
)
model.fit(X, y)

print(model)                 # the full Pareto front, one row per complexity
print(model.sympy())         # the selected equation as a SymPy expression
print(model.latex())         # ... and as LaTeX
```

`model.fit` runs the evolutionary search and writes a `hall_of_fame` file plus a pickle you
can reload with `PySRRegressor.from_file(...)`. Give PySR named columns by passing a pandas
`DataFrame` (variable names then appear in the equations instead of `x0, x1`).

## Read the Pareto front, do not take the last row

The most complex equation is almost never the answer. Inspect the front directly:

```python
front = model.equations_   # DataFrame: complexity, loss, score, equation, sympy_format, ...
```

- `loss` is the fitting error; it decreases monotonically with `complexity`.
- `score` measures how much each added unit of complexity buys — a **spike in `score`**
  marks the equation where extra terms suddenly stopped helping. That is your candidate law.
- `model.sympy()` / `model.predict(X)` return the equation chosen by `model_selection`
  (`"best"` = accuracy-vs-complexity tradeoff, default; `"accuracy"` = lowest loss).
- Select any specific row explicitly: `model.predict(X, index)` or `model.sympy(index)`.

Full front-interpretation recipe and a Pareto plot are in
[references/tuning-and-failure-modes.md](references/tuning-and-failure-modes.md).

## Physics-constrained search (dimensional analysis)

If you know the units of each input and the output, tell PySR — it will penalize
dimensionally inconsistent candidates and collapse the search space dramatically. Pass unit
strings (DynamicQuantities.jl syntax, e.g. `"kg * m / s^2"`, `"Constants.M_sun"`) to `fit`,
and set a large `dimensional_constraint_penalty` on the constructor:

```python
model.fit(X, y, X_units=["m", "kg", "s"], y_units="m / s^2")
```

Worked Kepler / Newton-gravitation examples, the unit-string syntax, and how this interacts
with `complexity_of_constants` are in
[references/dimensional-analysis.md](references/dimensional-analysis.md). For choosing which
dimensionless groups to feed in first, see `dimensional-analysis`.

## Key parameters

| Parameter | Typical | Role |
|---|---|---|
| `niterations` | 40-100 | Evolutionary iterations; more = better but slower |
| `binary_operators` | `["+","-","*","/"]` | Allowed 2-arg ops (add `^` cautiously) |
| `unary_operators` | `[]` | Allowed 1-arg ops (`sin`, `exp`, `sqrt`, ...) |
| `maxsize` | 20-30 | Max expression-tree nodes (complexity ceiling) |
| `parsimony` | 0.003-0.01 | Per-node complexity penalty (higher → simpler) |
| `populations` | 15-30 | Independent populations (parallel diversity) |
| `model_selection` | `"best"` | Which front row `predict`/`sympy` return |
| `deterministic` | `False` | `True` needs `parallelism="serial"` + `random_state` |

The complete parameter set — `nested_constraints`, `constraints`, `complexity_of_*`,
`extra_sympy_mappings` (custom operators), `elementwise_loss` (custom loss),
`select_k_features`, `warm_start`, `maxdepth`, `ncycles_per_iteration` — plus every output
method (`.equations_`, `.predict`, `.sympy`, `.latex`, `.latex_table`, `.from_file`) is in
[references/api-reference.md](references/api-reference.md).

## Common failure modes

- **Only finds constants** → data too noisy or too few points; clean it, add points, or
  raise `niterations`.
- **Equations too complex / overfit** → raise `parsimony`, lower `maxsize`, constrain
  operator nesting (no `sin(sin(x))`, `exp(exp(x))`).
- **Misses the true law** → add the operator it needs (`sin` for periodicity, `exp` for
  decay); normalize inputs to O(1) so constants stay searchable.
- **Non-reproducible runs** → set `deterministic=True`, `parallelism="serial"`,
  `random_state=0` (slower, single-threaded).

Full troubleshooting table, multi-output and custom-operator recipes, and scaling advice are
in [references/tuning-and-failure-modes.md](references/tuning-and-failure-modes.md) and
[references/worked-examples.md](references/worked-examples.md).

## References

- [references/api-reference.md](references/api-reference.md) — full constructor parameters,
  operator/constraint options, custom operators and losses, output/serialization methods,
  backend-parallelism knobs.
- [references/dimensional-analysis.md](references/dimensional-analysis.md) — unit-constrained
  search: `X_units`/`y_units` syntax, `dimensional_constraint_penalty`, Kepler and gravitation
  worked examples.
- [references/tuning-and-failure-modes.md](references/tuning-and-failure-modes.md) — Pareto
  interpretation, tuning heuristics for physics, noise/high-dimensional handling, full
  troubleshooting table.
- [references/worked-examples.md](references/worked-examples.md) — basic discovery,
  multi-output force fields, custom operators with nesting constraints, Pareto-front plotting.
