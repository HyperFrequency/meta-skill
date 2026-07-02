---
name: pymoo
version: 0.1.0
description: Multi- and single-objective optimization framework (pymoo). NSGA-II/III, MOEA/D, SPEA2, RVEA, Pareto fronts, constraint handling, MCDM, genetic-operator customization, benchmarks (ZDT, DTLZ, WFG), mixed-variable and parallel evaluation, for engineering design and trade-off optimization. Use when finding Pareto-optimal trade-offs, running evolutionary/metaheuristic algorithms, or benchmarking on standard test problems. NOT for convex/LP/QP or single smooth objectives with available gradients (use scipy.optimize or cvxpy), NOT for real-time/online optimization or deep-learning training (use PyTorch/JAX optimizers), NOT for hyperparameter search alone (use Optuna directly), and NOT a backtester or RL trainer (see vectorbt / stable-baselines3).
license: Apache-2.0 license
allowed-tools: Read Write Edit Bash
compatibility: Requires Python 3.10+ and pymoo (uv pip install). Optional matplotlib for visualization; optional autograd for gradient-based features; optional joblib for JoblibParallelization.
metadata: {"version": "1.1", "skill-author": "K-Dense Inc."}
---

# Pymoo - Multi-Objective Optimization in Python

Router for pymoo, a Python framework for single-, multi-, and many-objective
optimization via evolutionary and metaheuristic algorithms. Excels at finding
trade-off solutions (Pareto fronts) for problems with conflicting objectives.
Current stable release: **pymoo 0.6.2** (NumPy 2.x compatible since 0.6.1.3).
Keep this file lean — detailed code, tables, and guides live in `references/`.

## When to Use

- Optimizing one or multiple (especially conflicting) objectives
- Finding Pareto-optimal solutions and analyzing trade-offs
- Evolutionary / metaheuristic algorithms (GA, DE, PSO, CMA-ES, NSGA-II/III, MOEA/D)
- Constrained, mixed-variable (continuous/integer/binary/categorical), or dynamic problems
- Benchmarking on standard test problems (ZDT, DTLZ, WFG)
- Customizing genetic operators or making decisions from a Pareto front (MCDM)

## When NOT to Use

- Convex / LP / QP problems, or a single smooth objective with gradients available → use `scipy.optimize`, `cvxpy`
- Real-time / online optimization, or neural-network training → use PyTorch/JAX optimizers
- Pure hyperparameter search → use Optuna directly (pymoo only wraps it for mixed-variable SOO)
- Strategy backtesting or RL → see sibling skills `vectorbt`, `stable-baselines3`

## Installation

```bash
uv pip install pymoo            # or pin: "pymoo==0.6.2"
```

Docs: https://pymoo.org/ — LLM-friendly index: https://pymoo.org/llms.txt

## Core Mental Model

One unified `minimize()` drives every task — you swap the `problem` and `algorithm`:

```python
from pymoo.optimize import minimize
result = minimize(problem, algorithm, termination, seed=1, verbose=True)
```

**Result object:** `result.X` (decision variables), `result.F` (objective values),
`result.G` / `result.CV` (constraint values / total violation), `result.algorithm` (history).

**Problem definition styles** — pick one:
- `Problem`: vectorized `_evaluate` (receives a batch matrix)
- `ElementwiseProblem`: one solution per call — recommended for custom problems and parallel evaluation
- `FunctionalProblem`: objectives/constraints as plain functions, no subclassing

**Constraint convention:** inequalities as `g(x) <= 0` (feasible when ≤ 0), equalities as
`h(x) = 0`; convert `g(x) >= b` to `-(g(x) - b) <= 0`. NSGA-III requires reference directions.

## Workflows → `references/workflows.md`

Step-by-step, runnable recipes for each task. Match your situation to a workflow:

| # | Workflow | When |
|---|----------|------|
| 1 | Single-objective optimization | One objective (GA/DE/PSO/CMA-ES) |
| 2 | Multi-objective (2-3 obj) | Pareto front with NSGA-II |
| 3 | Many-objective (4+ obj) | NSGA-III + reference directions |
| 4 | Custom problem definition | Subclass `ElementwiseProblem` |
| 5 | Constraint handling | Feasibility-first, penalty, as-objective, SRES |
| 6 | Decision making from Pareto front | MCDM: pseudo-weights, knee point |
| 7 | Visualization | Scatter / 3D / PCP / Petal by objective count |
| 8 | Parallel evaluation | Expensive `_evaluate` (Starmap/Joblib runners) |
| 9 | Mixed-variable optimization | `vars` dict + `MixedVariableGA` |

`references/workflows.md` also holds the algorithm-selection guide, benchmark-problem
access snippets, operator-customization basics, and the troubleshooting checklist.

## Reference Files

- **algorithms.md** — every algorithm (SOO/MOO/many-obj/constrained/dynamic) with parameters and selection guidelines
- **problems.md** — benchmark test problems (ZDT, DTLZ, WFG) and their characteristics
- **operators.md** — sampling, selection, crossover, mutation, repair operators with configuration
- **visualization.md** — all plot types (Scatter, PCP, Petal, Heatmap, …) with a selection guide
- **constraints_mcdm.md** — constraint-handling techniques and multi-criteria decision-making methods
- **parallelization.md** — Starmap/process-pool/Joblib runners and pickling notes

Search references: `grep -ri "NSGA-III\|MOEA/D\|knee point" references/`

## Runnable Examples → `scripts/`

```bash
python3 scripts/single_objective_example.py
python3 scripts/multi_objective_example.py
python3 scripts/many_objective_example.py
python3 scripts/custom_problem_example.py
python3 scripts/decision_making_example.py
```

## Best Practices

Normalize objectives when scales differ; set a seed for reproducibility; use
`save_history=True` to study convergence; compare against the true Pareto front when
known; choose termination deliberately (`('n_gen', N)`, `('n_evals', N)`, or
`get_termination("f_tol", tol=0.001)`).
