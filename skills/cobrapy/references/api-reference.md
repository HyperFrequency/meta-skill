# COBRApy API Reference

Signatures, parameters, object attributes, and reusable code patterns. Keep the
router `SKILL.md` for the "when/why"; this file is the "exact how". Signatures track
the stable COBRApy API; confirm optional-kwarg defaults against the version you have
installed (`cobra.__version__`).

## Model I/O

```python
from cobra.io import (
    load_model, read_sbml_model, load_json_model, load_yaml_model, load_matlab_model,
    write_sbml_model, save_json_model, save_yaml_model, save_matlab_model,
)

# Bundled models — load offline, no network (these exact names, not arbitrary ids)
load_model("textbook")    # E. coli core (~95 reactions)
load_model("iJO1366")     # genome-scale E. coli   (NOTE: "ecoli" is NOT a valid id)
load_model("salmonella")  # genome-scale S. Typhimurium
# Any other id is fetched from BiGG / BioModels and cached. There is NO bundled
# "universal" model — supply your own candidate-reaction DB for gapfilling.

# Read
read_sbml_model(filename, f_replace={}, **kwargs)
load_json_model(filename)
load_yaml_model(filename)
load_matlab_model(filename, variable_name=None)

# Write
write_sbml_model(model, filename, f_replace={}, **kwargs)
save_json_model(model, filename, pretty=False, **kwargs)
save_yaml_model(model, filename, **kwargs)
save_matlab_model(model, filename, **kwargs)
```

Rule of thumb: SBML (`.xml`) for archival/interchange, JSON for Escher, YAML for
human-diffable review, MATLAB for legacy toolboxes.

## Core Classes

```python
from cobra import Model, Reaction, Metabolite, Gene

Model(id_or_model=None, name=None)
Metabolite(id=None, formula=None, name="", charge=None, compartment=None)
Reaction(id=None, name="", subsystem="", lower_bound=0.0, upper_bound=None)
Gene(id=None, name="", functional=True)
```

## Model Attributes

```python
model.reactions            # DictList[Reaction]
model.metabolites          # DictList[Metabolite]
model.genes                # DictList[Gene]

model.exchanges            # system-boundary exchange reactions
model.demands              # intracellular sinks (one-directional removal)
model.sinks                # intracellular reversible exchange
model.boundary             # all boundary reactions

model.objective            # read/write; accepts an ID, Reaction, or {Reaction: coeff}
model.objective_direction  # "max" | "min"
model.medium               # dict {exchange_id: max_uptake} — a computed view (reassign to change)
model.solver               # optlang solver interface
```

### DictList access

```python
model.reactions[0]                                  # by position
model.reactions.get_by_id("PFK")                    # by ID (KeyError if absent)
model.reactions.PFK                                 # attribute sugar for get_by_id
"PFK" in model.reactions                            # membership
model.reactions.query("atp")                        # substring match on id/name (case-insensitive)
model.reactions.query(lambda r: r.subsystem == "Glycolysis")   # predicate match
[r for r in model.reactions if r.lower_bound < 0]   # reversible reactions
```

## Optimization

```python
solution = model.optimize()          # Solution object
solution.objective_value             # float
solution.status                      # "optimal", "infeasible", "unbounded", ...
solution.fluxes                      # Series[reaction_id -> flux]
solution.shadow_prices               # Series[metabolite_id -> shadow price]
solution.reduced_costs               # Series[reaction_id -> reduced cost]

model.slim_optimize()                # returns float only (fast; NaN if not optimal)

# Retarget objective (all equivalent forms)
model.objective = "ATPM"
model.objective = model.reactions.ATPM
model.objective = {model.reactions.ATPM: 1.0}
model.objective_direction = "max"
```

### Solver configuration

```python
from cobra.util.solver import solvers
print(solvers)                       # what is installed

model.solver = "glpk"                # or "cplex", "gurobi" (need license)
model.solver.configuration.timeout = 60
model.solver.configuration.tolerances.feasibility = 1e-9
```

## Flux Analysis (`cobra.flux_analysis`)

### FBA variants

```python
pfba(model, fraction_of_optimum=1.0, **kwargs)          # parsimonious FBA
geometric_fba(model, epsilon=1e-06, max_tries=200)      # central point of optimal space
```

### Flux Variability Analysis

```python
flux_variability_analysis(
    model,
    reaction_list=None,       # None = all reactions
    loopless=False,           # remove thermodynamically infeasible internal loops
    fraction_of_optimum=1.0,  # 0.0–1.0 objective floor
    pfba_factor=None,
    processes=1,
)   # -> DataFrame[minimum, maximum]
```

### Deletions

```python
single_gene_deletion(model, gene_list=None, processes=1, **kwargs)
single_reaction_deletion(model, reaction_list=None, processes=1, **kwargs)
double_gene_deletion(model, gene_list1=None, gene_list2=None, processes=1, **kwargs)
double_reaction_deletion(model, reaction_list1=None, reaction_list2=None, processes=1, **kwargs)
# -> DataFrame[ids, growth, status]; double deletions use a MultiIndex of pairs
```

### Essentiality / blocked reactions

```python
find_essential_genes(model, threshold=0.01)
find_essential_reactions(model, threshold=0.01)
find_blocked_reactions(model, reaction_list=None, zero_cutoff=1e-9, open_exchanges=False)
```

### Flux sampling

```python
from cobra.sampling import sample, OptGPSampler, ACHRSampler

sample(model, n, method="optgp", thinning=100, processes=1, seed=None)   # -> DataFrame

sampler = OptGPSampler(model, processes=4, thinning=100)                 # parallel
sampler = ACHRSampler(model, thinning=100)                               # serial
samples = sampler.sample(n)
validation = sampler.validate(sampler.samples)   # per-sample codes:
#   'v' valid | 'l' lower-bound violation | 'u' upper-bound violation | 'e' equality violation
sampler.batch(n_samples, n_batches)              # generator of batches
```

Healthy sample sets are all `'v'`. Anything else signals a numerically stiff model —
tighten solver tolerances or switch solvers before analyzing the distribution.

### Production envelope

```python
production_envelope(
    model,
    reactions,             # 1–2 control reaction IDs
    objective=None,        # None = current model objective
    carbon_sources=None,   # enables carbon_yield_* columns
    points=20,
    threshold=0.01,
)
# -> DataFrame: control-reaction fluxes + flux_minimum/flux_maximum
#    (+ carbon_source, carbon_yield_*, mass_yield_* when a carbon source is given)
```

### Gapfilling

```python
gapfill(
    model,
    universal=None,          # model supplying candidate reactions
    lower_bound=0.05,        # required objective flux after filling
    penalties=None,          # {reaction_id: cost}
    demand_reactions=True,
    exchange_reactions=False,
    iterations=1,
)   # -> list[Reaction] to add
```

To enumerate alternative gapfill solutions, loop and raise penalties on already-found
reactions so the search does not return the same set.

## Media and Boundaries

```python
# Medium is a view — copy, mutate, reassign
medium = model.medium
medium["EX_glc__D_e"] = 10.0
model.medium = medium

from cobra.medium import minimal_medium
minimal_medium(
    model,
    min_objective_value=0.1,
    exports=False,
    minimize_components=False,   # True => MILP: fewest components (slower)
    open_exchanges=False,
)   # -> Series[exchange_id -> flux]  (DataFrame if minimize_components is an int)

model.add_boundary(metabolite, type="exchange", reaction_id=None, lb=None, ub=None, sbo_term=None)
# type in {"exchange", "demand", "sink"}
```

## Manipulation

```python
# Add
model.add_reactions([rxn1, rxn2])
model.add_metabolites([met1, met2])
rxn.add_metabolites({met_a: -1.0, met_b: 1.0})     # negative = consumed, positive = produced

# Remove
model.remove_reactions(["PFK", "FBA"])              # accepts IDs or Reaction objects
model.remove_metabolites([met1])                    # also strips them from reactions

# Modify
rxn.bounds = (0.0, 1000.0)                           # set both together
rxn.gene_reaction_rule = "(b1 and b2) or b3"
rxn.subtract_metabolites({met: 1.0})
rxn.knock_out()                                      # lower_bound = upper_bound = 0
gene.knock_out()

# Copy
model.copy()                                         # deep, independent
```

## Object Attributes

### Reaction

```python
rxn.id, rxn.name, rxn.subsystem
rxn.bounds, rxn.lower_bound, rxn.upper_bound, rxn.reversibility
rxn.gene_reaction_rule, rxn.genes            # set[Gene]
rxn.metabolites                              # {Metabolite: stoichiometry}
rxn.reaction                                 # equation string
rxn.build_reaction_string()
rxn.check_mass_balance()                     # {} if balanced, else element imbalances
rxn.get_coefficient(metabolite_id)
```

### Metabolite

```python
met.id, met.name, met.formula, met.charge, met.compartment
met.reactions                                # frozenset[Reaction]
met.summary()                                # production/consumption breakdown
```

### Gene

```python
gene.id, gene.name, gene.functional
gene.reactions                               # frozenset[Reaction]
gene.knock_out()
```

## Context Management

```python
with model:
    model.objective = "ATPM"
    model.reactions.EX_glc__D_e.lower_bound = -5.0
    model.genes.b0008.knock_out()
    solution = model.optimize()
# every change above is rolled back here

# Nesting works and unwinds in reverse
with model:
    model.objective = "ATPM"
    with model:
        model.genes.b0008.knock_out()   # both active
    # only objective change active
```

Use context managers for *any* temporary edit. They are the difference between a
clean parameter scan and a slowly-corrupting model state.

## Building a Model From Scratch

```python
from cobra import Model, Reaction, Metabolite

model = Model("my_model")

atp = Metabolite("atp_c", formula="C10H12N5O13P3", name="ATP", compartment="c")
adp = Metabolite("adp_c", formula="C10H12N5O10P2", name="ADP", compartment="c")
pi  = Metabolite("pi_c",  formula="HO4P",          name="Phosphate", compartment="c")

rxn = Reaction("ATPASE", name="ATP hydrolysis", subsystem="Energy")
rxn.bounds = (0.0, 1000.0)
rxn.add_metabolites({atp: -1.0, adp: 1.0, pi: 1.0})
rxn.gene_reaction_rule = "(gene1 and gene2) or gene3"

model.add_reactions([rxn])
model.add_boundary(atp, type="exchange")
model.add_boundary(adp, type="demand")
model.objective = "ATPASE"
```

## Validation and Statistics

```python
model.summary()                       # objective + top uptakes/secretions
model.metabolites.atp_c.summary()     # who produces/consumes this metabolite
model.reactions.PFK.summary()
model.summary(fva=0.95)               # summary with FVA at 95% optimality

len(model.reactions), len(model.metabolites), len(model.genes)

# Mass balance sweep
unbalanced = {r.id: r.check_mass_balance() for r in model.reactions if r.check_mass_balance()}
```

## Reusable Patterns

### Batch over conditions

```python
results = []
for condition in conditions:
    with model:
        apply(model, condition)
        sol = model.optimize()
        results.append({"condition": condition,
                        "growth": sol.objective_value,
                        "status": sol.status})
df = pd.DataFrame(results)
```

### Systematic single knockout

```python
rows = []
for gene in model.genes:
    with model:
        gene.knock_out()
        sol = model.optimize()
        rows.append({"gene": gene.id,
                     "growth": sol.objective_value if sol.status == "optimal" else 0.0,
                     "status": sol.status})
df = pd.DataFrame(rows)
```

### Parameter scan (e.g. uptake titration)

```python
import numpy as np
rows = []
for value in np.linspace(0, 20, 21):
    with model:
        model.reactions.EX_glc__D_e.lower_bound = -value
        sol = model.optimize()
        rows.append({"glucose_uptake": value,
                     "growth": sol.objective_value,
                     "acetate": sol.fluxes["EX_ac_e"]})
df = pd.DataFrame(rows)
```

Full API docs: https://cobrapy.readthedocs.io/
