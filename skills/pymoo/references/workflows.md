# Pymoo Workflows Reference

Step-by-step workflows with runnable examples. For algorithm internals see `algorithms.md`,
operators see `operators.md`, benchmark problems see `problems.md`, plots see `visualization.md`,
constraints/decision-making see `constraints_mcdm.md`, parallel evaluation see `parallelization.md`.

## Workflow 1: Single-Objective Optimization

**When:** Optimizing one objective function.

**Steps:** define/select problem → choose SOO algorithm (GA, DE, PSO, CMA-ES) → set termination → run → extract best.

```python
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.problems import get_problem
from pymoo.optimize import minimize

problem = get_problem("rastrigin", n_var=10)
algorithm = GA(pop_size=100, eliminate_duplicates=True)
result = minimize(problem, algorithm, ('n_gen', 200), seed=1, verbose=True)

print(f"Best solution: {result.X}")
print(f"Best objective: {result.F[0]}")
```

See `scripts/single_objective_example.py`.

## Workflow 2: Multi-Objective Optimization (2-3 objectives)

**When:** 2-3 conflicting objectives, need a Pareto front. **Algorithm:** NSGA-II.

```python
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.problems import get_problem
from pymoo.optimize import minimize
from pymoo.visualization.scatter import Scatter

problem = get_problem("zdt1")
algorithm = NSGA2(pop_size=100)
result = minimize(problem, algorithm, ('n_gen', 200), seed=1)

plot = Scatter()
plot.add(result.F, label="Obtained Front")
plot.add(problem.pareto_front(), label="True Front", alpha=0.3)
plot.show()
print(f"Found {len(result.F)} Pareto-optimal solutions")
```

See `scripts/multi_objective_example.py`.

## Workflow 3: Many-Objective Optimization (4+ objectives)

**When:** 4+ objectives. **Algorithm:** NSGA-III (requires reference directions).

```python
from pymoo.algorithms.moo.nsga3 import NSGA3
from pymoo.problems import get_problem
from pymoo.optimize import minimize
from pymoo.util.ref_dirs import get_reference_directions
from pymoo.visualization.pcp import PCP

problem = get_problem("dtlz2", n_obj=5)
ref_dirs = get_reference_directions("das-dennis", n_dim=5, n_partitions=12)
algorithm = NSGA3(ref_dirs=ref_dirs)
result = minimize(problem, algorithm, ('n_gen', 300), seed=1)

plot = PCP(labels=[f"f{i+1}" for i in range(5)])
plot.add(result.F, alpha=0.3)
plot.show()
```

See `scripts/many_objective_example.py`.

## Workflow 4: Custom Problem Definition

**When:** Domain-specific problem. Extend `ElementwiseProblem`, set dimensions/bounds in `__init__`,
implement `_evaluate`.

**Unconstrained:**
```python
from pymoo.core.problem import ElementwiseProblem
import numpy as np

class MyProblem(ElementwiseProblem):
    def __init__(self):
        super().__init__(n_var=2, n_obj=2, xl=np.array([0, 0]), xu=np.array([5, 5]))

    def _evaluate(self, x, out, *args, **kwargs):
        f1 = x[0]**2 + x[1]**2
        f2 = (x[0]-1)**2 + (x[1]-1)**2
        out["F"] = [f1, f2]
```

**Constrained:**
```python
class ConstrainedProblem(ElementwiseProblem):
    def __init__(self):
        super().__init__(n_var=2, n_obj=2, n_ieq_constr=2, n_eq_constr=1,
                         xl=np.array([0, 0]), xu=np.array([5, 5]))

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"] = [f1, f2]
        out["G"] = [g1, g2]   # inequality, feasible when <= 0
        out["H"] = [h1]       # equality, feasible when = 0
```

**Constraint formulation rules:**
- Inequality: express as `g(x) <= 0` (feasible when ≤ 0).
- Equality: express as `h(x) = 0` (feasible when = 0).
- Convert `g(x) >= b` to `-(g(x) - b) <= 0`.

See `scripts/custom_problem_example.py`.

## Workflow 5: Constraint Handling

**When:** Problem has feasibility constraints. Full guide in `references/constraints_mcdm.md`.

```python
# 1. Feasibility First (default, recommended) — works automatically
from pymoo.algorithms.moo.nsga2 import NSGA2
algorithm = NSGA2(pop_size=100)
result = minimize(problem, algorithm, termination)
feasible = result.CV[:, 0] == 0   # CV = constraint violation
print(f"Feasible solutions: {np.sum(feasible)}")

# 2. Penalty method
from pymoo.constraints.as_penalty import ConstraintsAsPenalty
problem_penalized = ConstraintsAsPenalty(problem, penalty=1e6)

# 3. Constraint as objective
from pymoo.constraints.as_obj import ConstraintsAsObjective
problem_with_cv = ConstraintsAsObjective(problem)

# 4. Specialized algorithm with built-in handling
from pymoo.algorithms.soo.nonconvex.sres import SRES
algorithm = SRES()
```

## Workflow 6: Decision Making from Pareto Front

**When:** Have a Pareto front, need to select preferred solution(s). Full methods in `references/constraints_mcdm.md`.

```python
from pymoo.mcdm.pseudo_weights import PseudoWeights
import numpy as np

F_norm = (result.F - result.F.min(axis=0)) / (result.F.max(axis=0) - result.F.min(axis=0))
weights = np.array([0.3, 0.7])   # must sum to 1
selected_idx = PseudoWeights(weights).do(F_norm)
best_solution = result.X[selected_idx]
best_objectives = result.F[selected_idx]
```

Other MCDM methods: Compromise Programming (closest to ideal), Knee Point (balanced trade-off),
Hypervolume Contribution (most diverse subset). See `scripts/decision_making_example.py`.

## Workflow 7: Visualization

Choose by number of objectives (full catalogue in `references/visualization.md`):

```python
# 2 objectives: Scatter
from pymoo.visualization.scatter import Scatter
Scatter(title="Bi-objective").add(result.F, color="blue", alpha=0.7).show()

# 3 objectives: Scatter auto-renders in 3D
Scatter(title="Tri-objective").add(result.F).show()

# 4+ objectives: Parallel Coordinate Plot
from pymoo.visualization.pcp import PCP
PCP(labels=[f"f{i+1}" for i in range(n_obj)], normalize_each_axis=True).add(result.F, alpha=0.3).show()

# Solution comparison: Petal
from pymoo.visualization.petal import Petal
plot = Petal(bounds=[result.F.min(axis=0), result.F.max(axis=0)], labels=["Cost", "Weight", "Efficiency"])
plot.add(solution_A, label="Design A")
plot.add(solution_B, label="Design B")
plot.show()
```

## Workflow 8: Parallel Evaluation

**When:** Each `_evaluate` call is expensive (simulations, ML models, external solvers). Pass an
`elementwise_runner` to `ElementwiseProblem`. Full guide (process pools, joblib, pickling) in
`references/parallelization.md`.

```python
from multiprocessing.pool import ThreadPool
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from pymoo.parallelization.starmap import StarmapParallelization

class MyProblem(ElementwiseProblem):
    def __init__(self, elementwise_runner=None, **kwargs):
        super().__init__(n_var=10, n_obj=1, xl=-5, xu=5,
                         elementwise_runner=elementwise_runner, **kwargs)

    def _evaluate(self, x, out, *args, **kwargs):
        out["F"] = (x ** 2).sum()   # replace with expensive evaluation

pool = ThreadPool(4)
runner = StarmapParallelization(pool.starmap)
problem = MyProblem(elementwise_runner=runner)
result = minimize(problem, GA(), ("n_gen", 50), seed=1)
pool.close()
```

## Workflow 9: Mixed-Variable Optimization

**When:** Variables include continuous, integer, binary, and/or categorical types. Define a `vars`
dict with typed variables; use `MixedVariableGA`.

```python
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.variable import Real, Integer, Choice, Binary
from pymoo.core.mixed import MixedVariableGA
from pymoo.optimize import minimize

class MixedProblem(ElementwiseProblem):
    def __init__(self, **kwargs):
        vars = {
            "b": Binary(),
            "x": Choice(options=["nothing", "multiply"]),
            "y": Integer(bounds=(0, 2)),
            "z": Real(bounds=(0, 5)),
        }
        super().__init__(vars=vars, n_obj=1, **kwargs)

    def _evaluate(self, X, out, *args, **kwargs):
        b, x, z, y = X["b"], X["x"], X["z"], X["y"]
        f = z + y
        if b:
            f = 100 * f
        if x == "multiply":
            f = 10 * f
        out["F"] = f

algorithm = MixedVariableGA(pop_size=20)
result = minimize(MixedProblem(), algorithm, ("n_evals", 1000), seed=1)
```

For multi-objective mixed-variable problems, use
`MixedVariableGA(pop_size=20, survival=RankAndCrowdingSurvival())`. For single-objective mixed
search, pymoo also wraps [Optuna](https://optuna.org) via
`pymoo.algorithms.soo.nonconvex.optuna.Optuna`. See `references/algorithms.md`.

## Algorithm Selection Guide

**Single-objective**

| Algorithm | Best For | Key Features |
|-----------|----------|--------------|
| **GA** | General-purpose | Flexible, customizable operators |
| **DE** | Continuous optimization | Good global search |
| **PSO** | Smooth landscapes | Fast convergence |
| **CMA-ES** | Difficult/noisy problems | Self-adapting |

**Multi-objective (2-3 objectives)**

| Algorithm | Best For | Key Features |
|-----------|----------|--------------|
| **NSGA-II** | Standard benchmark | Fast, reliable, well-tested |
| **SPEA2** | Archive-based MOO | Strength-based fitness, external archive |
| **R-NSGA-II** | Preference regions | Reference point guidance |
| **MOEA/D** | Decomposable problems | Scalarization approach |

**Many-objective (4+ objectives)**

| Algorithm | Best For | Key Features |
|-----------|----------|--------------|
| **NSGA-III** | 4-15 objectives | Reference direction-based |
| **RVEA** | Adaptive search | Reference vector evolution |
| **AGE-MOEA** | Complex landscapes | Adaptive geometry |

**Constrained**

| Approach | Algorithm | When to Use |
|----------|-----------|-------------|
| Feasibility-first | Any algorithm | Large feasible region |
| Specialized | SRES, ISRES | Heavy constraints |
| Penalty | GA + penalty | Algorithm compatibility |

Full parameter reference in `references/algorithms.md`.

## Benchmark Problem Access

```python
from pymoo.problems import get_problem

# Single-objective
problem = get_problem("rastrigin", n_var=10)
problem = get_problem("rosenbrock", n_var=10)

# Multi-objective
problem = get_problem("zdt1")        # Convex front
problem = get_problem("zdt2")        # Non-convex front
problem = get_problem("zdt3")        # Disconnected front

# Many-objective
problem = get_problem("dtlz2", n_obj=5, n_var=12)
problem = get_problem("dtlz7", n_obj=4)
```

Full catalogue in `references/problems.md`.

## Genetic Operator Customization

```python
from pymoo.algorithms.soo.nonconvex.ga import GA
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM

algorithm = GA(pop_size=100, crossover=SBX(prob=0.9, eta=15),
               mutation=PM(eta=20), eliminate_duplicates=True)
```

Operator selection by variable type:
- **Continuous:** crossover SBX (Simulated Binary Crossover); mutation PM (Polynomial Mutation).
- **Binary:** crossover TwoPointCrossover / UniformCrossover; mutation BitflipMutation.
- **Permutations (TSP, scheduling):** crossover OrderCrossover (OX); mutation InversionMutation.

Full reference in `references/operators.md`.

## Performance and Troubleshooting

**Algorithm not converging:** increase population size; increase generations; try a different
algorithm if multimodal; verify constraint formulation.

**Poor Pareto front distribution:** for NSGA-III adjust reference directions; increase population
size; enable duplicate elimination; verify problem scaling.

**Few feasible solutions:** use constraint-as-objective; apply repair operators; try SRES/ISRES;
check constraints are `g <= 0`.

**High computational cost:** reduce population/generations; use simpler operators; enable parallel
evaluation via `elementwise_runner` (Workflow 8).

**Best practices:**
1. Normalize objectives when scales differ significantly.
2. Set a random `seed` for reproducibility.
3. `save_history=True` to analyze convergence.
4. Visualize results to gauge solution quality.
5. Compare with the true Pareto front when available.
6. Use appropriate termination (generations, evaluations, tolerance).
7. Tune operator parameters to problem characteristics.
</content>
</invoke>
