# Tuning, Pareto Interpretation, and Failure Modes

## Interpreting the Pareto front

`model.equations_` is a DataFrame with one row per complexity level actually reached. The key
columns:

- `complexity` — number of nodes in the expression tree.
- `loss` — fitting error (by default MSE); strictly non-increasing as complexity grows.
- `score` — the marginal value of complexity: roughly `-Δ log(loss) / Δ complexity` between
  adjacent rows. A **large `score` spike** is the equation where adding a term suddenly bought
  a big accuracy jump; beyond it, extra terms buy little. That elbow is your candidate law.

Plot it to see the elbow:

```python
import matplotlib.pyplot as plt

front = model.equations_
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(front["complexity"], front["loss"], "o-", color="steelblue")
best = front["score"].idxmax()                     # the biggest score spike
ax.plot(front.loc[best, "complexity"], front.loc[best, "loss"],
        "r*", markersize=16, label="max score (elbow)")
ax.set(xlabel="complexity", ylabel="loss", yscale="log",
       title="Accuracy vs complexity")
ax.legend()
fig.savefig("pareto_front.png", dpi=150, bbox_inches="tight")

for _, r in front.iterrows():
    print(f"  c={int(r['complexity']):2d}  loss={r['loss']:.3e}  {r['equation']}")
```

Do not reflexively take the lowest-loss (most complex) row — that is where overfitting lives.
`model_selection="best"` already targets the elbow; `"accuracy"` targets lowest loss.

## Tuning heuristics for physics

1. **Start minimal.** `["+", "-", "*", "/"]` only. Add one unary operator at a time and only
   with a physical reason: `sin`/`cos` for periodicity, `exp`/`log` for growth/decay, `sqrt`/
   `square` for power-law structure.
2. **Keep it parsimonious.** Real laws are small. `parsimony=0.005-0.01` and `maxsize=15-25`
   are good starting points; loosen only if the front never fits the data well.
3. **Constrain nesting.** Ban physically implausible stacks: `nested_constraints={"sin":
   {"sin": 0, "cos": 0}, "exp": {"exp": 0, "log": 0}, "log": {"exp": 0, "log": 0}}`.
4. **Normalize inputs to O(1).** Widely different scales make constants hard to search; scale
   variables (and remember the scaling when interpreting the result).
5. **Give it enough data.** 100-1000 points is typical; more helps against noise. Too few
   points → the search collapses to a constant.
6. **Add units when you have them.** See
   [dimensional-analysis.md](dimensional-analysis.md) — it prunes the space more than any
   tuning.
7. **Validate out-of-sample.** Test the chosen equation on held-out data and check dimensional
   consistency by hand. A formula that only fits the training range is not a law.

## High dimensionality

PySR is not a high-dimensional black-box learner. For more than ~6 raw inputs:

- Use `select_k_features=k` to let a random forest pick the `k` most relevant columns before
  the symbolic search runs.
- Or reduce dimensions first: form dimensionless groups (`dimensional-analysis`), or feed
  known physically-meaningful combinations rather than raw coordinates.

## Noise

- Heavy noise pushes the search toward constants. Clean/aggregate first, raise `niterations`,
  and increase sample count before loosening complexity.
- For known measurement-error structure, encode it with a custom `elementwise_loss`
  (weighted or robust) rather than pre-whitening — see
  [api-reference.md](api-reference.md).
- PySR has an optional `denoise=True` (kernel-regression pre-smoothing); use with care, it can
  erase real structure.

## Reproducibility

Bit-reproducible runs are slow and single-threaded:

```python
PySRRegressor(deterministic=True, parallelism="serial", random_state=0)
```

All three are required together — `deterministic=True` without `parallelism="serial"` will
error, and without `random_state` the run is not seeded.

## Troubleshooting table

| Symptom | Likely cause | Fix |
|---|---|---|
| First `import pysr` hangs ~2 min | Julia + backend installing (one-time) | Wait; ensure network access. Do not call `pysr.install()` (removed). |
| Search only returns a constant | Data too noisy, too few points, or missing operator | Clean data, add points, raise `niterations`, add the needed operator. |
| Equations overly complex / overfit | Complexity budget too loose | Raise `parsimony`, lower `maxsize`, add `nested_constraints`. |
| True law never appears | Required operator absent, or inputs unscaled | Add operator (`sin`, `exp`, ...); normalize inputs to O(1). |
| Runs are non-reproducible | Parallel, unseeded search | `deterministic=True`, `parallelism="serial"`, `random_state=0`. |
| Very slow | Too much search per iteration | Lower `maxsize`, `populations`, `niterations`, `ncycles_per_iteration`. |
| Dimensional run finds nothing | Penalty too high or wrong `y_units` | Verify unit strings; drop `dimensional_constraint_penalty` to test. |
| `.sympy()` fails on a custom op | No SymPy mapping for the Julia operator | Add it to `extra_sympy_mappings`. |
