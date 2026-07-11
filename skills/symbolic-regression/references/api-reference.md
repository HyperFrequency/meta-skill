# PySR API Reference

`PySRRegressor` follows the scikit-learn estimator convention: construct with search options,
`.fit(X, y)`, then read equations from the fitted object. `X` is `(n_samples, n_features)`
(NumPy array or pandas DataFrame — a DataFrame gives you named variables in the equations); `y`
is `(n_samples,)` or `(n_samples, n_targets)` for multi-output.

## Search-space parameters

| Parameter | Default | Meaning |
|---|---|---|
| `binary_operators` | `["+","-","*","/"]` | Two-argument operators. `^` (pow) is supported but makes the space harder — add only when needed. |
| `unary_operators` | `[]` | One-argument operators: `sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, `square`, `cube`, `abs`, `neg`, `sign`, `atan`, ... You may define your own inline as `"inv(x) = 1/x"` (Julia syntax). |
| `maxsize` | 20 | Maximum number of nodes in an expression tree (hard complexity ceiling). |
| `maxdepth` | none | Optional maximum tree depth (independent of `maxsize`). |
| `parsimony` | 0.0032 | Multiplicative penalty added to loss per unit complexity. Higher → simpler equations. |
| `adaptive_parsimony_scaling` | ~20 | Scales parsimony across complexity levels so no complexity band is starved; raise if the front is sparse at some sizes. |
| `constraints` | `{}` | Per-operator limits on argument sizes, e.g. `{"^": (-1, 1)}` forbids large exponents/bases. Negative = unlimited. |
| `nested_constraints` | `{}` | Forbid/limit operator nesting, e.g. `{"sin": {"sin": 0, "cos": 0}}` bans `sin(sin(x))` and `sin(cos(x))`. |
| `complexity_of_operators` | `{}` | Override the complexity cost of specific operators (e.g. make `exp` cost 3). |
| `complexity_of_constants` | 1 | Complexity cost assigned to a numeric constant. Raise to discourage constant-stuffing. |
| `complexity_of_variables` | 1 | Complexity cost assigned to a variable leaf. |
| `select_k_features` | none | Pre-select the `k` most relevant features (random-forest importance) before searching — the way to handle moderate-to-high input dimensionality. |

## Custom operators and losses

- **Custom operator** — supply Julia source in the operator list and a Python/SymPy
  translation so `.sympy()` can round-trip it:

  ```python
  PySRRegressor(
      unary_operators=["inv(x) = 1/x"],
      extra_sympy_mappings={"inv": lambda x: 1 / x},
  )
  ```

- **Custom loss** — `elementwise_loss` takes a Julia string of a per-element loss, e.g.
  `elementwise_loss="loss(prediction, target) = (prediction - target)^2"`. For weighted or
  whole-batch objectives use `loss_function` instead (full Julia function). Use this to encode
  heteroscedastic weighting or robust losses.

## Evolution / performance parameters

| Parameter | Default | Meaning |
|---|---|---|
| `niterations` | 40 | Number of evolve↔migrate iterations. The main quality/time dial. |
| `populations` | 15 | Independent populations searched in parallel (diversity). |
| `population_size` | 33 | Members per population. |
| `ncycles_per_iteration` | ~550 | Mutation cycles between migrations; lower for faster feedback in tests. |
| `parallelism` | `"multithreading"` | `"multithreading"`, `"multiprocessing"`, or `"serial"`. Use `"serial"` for deterministic runs. |
| `numprocs` / `procs` | auto | Worker count for multiprocessing. |
| `turbo` / `bumper` | `False` | Experimental Julia speedups; enable if the search is CPU-bound. |
| `warm_start` | `False` | Continue evolving from the previous `.fit` state (append more `niterations`). |
| `random_state` | none | Seed. Combine with `deterministic=True` + `parallelism="serial"` for bit-reproducible runs. |
| `deterministic` | `False` | Forces reproducible search; requires serial parallelism and a `random_state`. Slower. |

## Reading results

| Call | Returns |
|---|---|
| `model.equations_` | pandas DataFrame of the whole Pareto front: `complexity`, `loss`, `score`, `equation`, `sympy_format`, `lambda_format`. For multi-output, a list of DataFrames. |
| `model.sympy(index=None)` | Selected equation (or row `index`) as a SymPy expression. |
| `model.latex(index=None)` | Selected equation as a LaTeX string. |
| `model.latex_table()` | The whole front rendered as a LaTeX table (for papers). |
| `model.predict(X, index=None)` | Evaluate the selected equation (or a chosen row) on new data. |
| `model.get_best()` | The selected row of the front as a pandas Series. |
| `model.model_selection` | `"best"` (accuracy-vs-complexity, default) or `"accuracy"` (lowest loss) — governs what `sympy`/`predict`/`get_best` return by default. |

## Save / load

`.fit` automatically writes a `hall_of_fame_*.csv` and a pickle in the run directory
(`output_directory` / `run_id` control where). Reload a finished search without re-running:

```python
model = PySRRegressor.from_file(run_directory="outputs/<run_id>")
```

(Older PySR exposed `from_file(pickle_filename)`; current versions take the run directory.
Check the installed version's signature with `help(PySRRegressor.from_file)`.)

## Version note

PySR is under active development and parameter names occasionally change across major versions
(the `procs`/`multithreading` knobs were unified into `parallelism`; `loss` was split into
`elementwise_loss`/`loss_function`). When a parameter is rejected, check the installed docs
(`PySRRegressor?` in IPython) rather than guessing. Do not call the removed `pysr.install()`.
