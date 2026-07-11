# Worked Examples

Self-contained recipes beyond the core workflow in `SKILL.md`. All assume:

```python
import numpy as np
from pysr import PySRRegressor
```

## 1. Basic discovery with named variables

Passing a pandas DataFrame makes the discovered equation use your column names instead of
`x0, x1`:

```python
import pandas as pd

rng = np.random.default_rng(0)
X = pd.DataFrame({
    "theta": rng.uniform(-np.pi, np.pi, 300),
    "L":     rng.uniform(0.5, 2.0, 300),
})
y = 9.81 / X["L"] * np.sin(X["theta"])      # angular acceleration of a pendulum

model = PySRRegressor(
    niterations=60,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["sin", "cos"],
    maxsize=20,
    parsimony=0.005,
)
model.fit(X, y)
print(model.sympy())     # ~ 9.81 * sin(theta) / L
```

## 2. Custom operators with nesting constraints

Add an inverse operator (Julia source + SymPy mapping) and forbid meaningless nestings:

```python
model = PySRRegressor(
    niterations=50,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["sqrt", "square", "inv(x) = 1/x"],
    extra_sympy_mappings={"inv": lambda x: 1 / x},
    nested_constraints={
        "sqrt": {"sqrt": 0},          # no sqrt(sqrt(x))
        "inv":  {"inv": 0},           # no 1/(1/x)
    },
    maxsize=25,
    parsimony=0.004,
)
```

Every custom unary operator you name in Julia (`"inv(x) = 1/x"`) needs a matching
`extra_sympy_mappings` entry, or `.sympy()` / `.latex()` cannot render the result.

## 3. Multi-output: a 2D force field

Fit each output component to its own equation. Pass a 2-column `y`, or fit two models — a
2-column `y` shares the search budget and returns a list of fronts:

```python
rng = np.random.default_rng(1)
X = rng.standard_normal((400, 2))
r3 = (X[:, 0] ** 2 + X[:, 1] ** 2) ** 1.5
Fx = -X[:, 0] / r3
Fy = -X[:, 1] / r3
Y = np.column_stack([Fx, Fy])       # inverse-square-law field

model = PySRRegressor(
    niterations=60,
    binary_operators=["+", "-", "*", "/"],
    unary_operators=["sqrt", "square"],
    maxsize=25,
)
model.fit(X, Y)

for k, front in enumerate(model.equations_):     # one DataFrame per output
    print(f"F_{k} = {model.sympy(index=None)[k] if False else front.iloc[-1]['equation']}")
# Or select per-output best equations directly:
print("Fx =", model.sympy()[0])
print("Fy =", model.sympy()[1])
```

For multi-output, `model.equations_` is a **list** of DataFrames and `model.sympy()` returns a
**list** of expressions — index by output.

## 4. Continue a search (warm start)

If a run needs more evolution, reuse its state instead of starting over:

```python
model = PySRRegressor(niterations=40, warm_start=True,
                      binary_operators=["+", "-", "*", "/"])
model.fit(X, y)          # first 40 iterations
model.fit(X, y)          # 40 more, continuing the same populations
```

## 5. Save results for a paper

```python
print(model.latex_table())              # whole Pareto front as a LaTeX table
best_eq = model.sympy()                 # SymPy object — differentiate, simplify, etc.
model.predict(X_test)                   # evaluate the selected equation on new data
model.predict(X_test, index=3)          # evaluate a specific (simpler) front row
```

Reload a finished search without recomputing:

```python
model = PySRRegressor.from_file(run_directory="outputs/<run_id>")
```

See [api-reference.md](api-reference.md) for the full method and parameter list, and
[dimensional-analysis.md](dimensional-analysis.md) for adding physical-unit constraints.
