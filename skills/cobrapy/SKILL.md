---
name: cobrapy
version: 0.1.0
description: >-
  Constraint-based reconstruction and analysis (COBRA) of genome-scale metabolic
  models with the COBRApy Python library. Use when you need flux balance analysis
  (FBA / pFBA / geometric FBA), flux variability analysis, single or double gene
  and reaction knockouts, flux sampling, minimal-media and growth-medium design,
  production envelopes, gapfilling, or reading/writing/building SBML/JSON/YAML
  metabolic models — the standard toolkit for systems biology, metabolic
  engineering, and strain design. Do NOT use for kinetic/ODE metabolic simulation
  (needs a kinetic solver), transcriptomic or single-cell analysis, sequence
  bioinformatics, generic linear programming unrelated to metabolism, or drawing
  interactive flux maps (export to Escher instead).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: GPL-2.0 (COBRApy)
---

# COBRApy — Constraint-Based Metabolic Modeling

## Overview

COBRApy is the reference Python library for constraint-based reconstruction and
analysis of genome-scale metabolic models. It formulates a stoichiometric model
as a linear program (steady-state mass balance `S · v = 0` plus per-reaction flux
bounds) and solves it to predict growth, secretion, essentiality, and achievable
production. Use it to load a published model, simulate metabolism under different
media and genetic perturbations, and design strains — without writing any LP by
hand.

This skill is a router. Short capability sections below cover the common tasks;
push deep signatures and full end-to-end scripts into the reference files:

- `references/api-reference.md` — function signatures, parameters, attributes, and reusable code patterns.
- `references/workflows.md` — complete step-by-step scripts (knockout screens, media design, flux-space exploration, strain design, model validation).

## When to Use This Skill

- Predict growth rate or the flux distribution of a metabolic model under a given medium (FBA).
- Find alternative-optimal flux ranges per reaction (FVA), or sample the feasible flux polytope.
- Screen single/double gene or reaction knockouts for essentiality or synthetic lethality.
- Compute minimal media, design growth conditions, or compare aerobic vs anaerobic requirements.
- Map production envelopes / phenotype phase planes and design a production strain for a target metabolite.
- Gapfill an infeasible model from a universal reaction database.
- Read, write, edit, or build metabolic models in SBML / JSON / YAML / MATLAB formats.

## When NOT to Use This Skill

- **Kinetic / dynamic simulation** with rate laws and concentrations over time — COBRA is steady-state and stoichiometric; use a kinetic ODE solver instead.
- **Transcriptomics, single-cell, or sequence bioinformatics** — different toolchains entirely.
- **Generic linear/mixed-integer programming** unrelated to metabolic networks — call an LP solver (or `optlang`) directly.
- **Interactive flux-map visualization** — export to Escher (`save_json_model`) and render there.
- Plotting results: hand distributions and heatmaps off to the `matplotlib` / `seaborn` sibling skills; COBRApy returns pandas objects that plot directly.

## Install and Sanity Check

```bash
pip install cobra          # pulls GLPK by default; add cplex/gurobi separately for speed
```

```python
from cobra.io import load_model
model = load_model("textbook")          # small E. coli core model, no download for tests
print(model.slim_optimize())            # ~0.874 /h — confirms the solver works
```

`slim_optimize()` returns only the objective value (fast); `optimize()` returns a
full `Solution`. Bundled models (shipped with cobrapy, load without network):
`"textbook"` (E. coli core), `"iJO1366"` (genome-scale E. coli), `"salmonella"`. Any
other id is fetched from BiGG / BioModels and cached on first use. There is **no**
bundled `"universal"` model — build or download a candidate-reaction database for
gapfilling (see below).

## Load and Save Models

```python
from cobra.io import read_sbml_model, load_json_model, load_yaml_model
model = read_sbml_model("model.xml")    # SBML is the interchange standard

from cobra.io import write_sbml_model, save_json_model
write_sbml_model(model, "out.xml")
save_json_model(model, "out.json")      # JSON is what Escher consumes
```

Prefer SBML for archival and exchange. See `references/api-reference.md` for the
full I/O matrix (MATLAB, YAML) and signatures.

## Inspect Model Structure

Reactions, metabolites, and genes are `DictList` objects — index like a list, look
up by ID like a dict, and substring-query:

```python
model.reactions.get_by_id("PFK")        # by ID
model.reactions[0]                       # by index
model.reactions.query("atp")            # case-insensitive substring match
rxn = model.reactions.PFK
rxn.reaction                             # stoichiometric equation string
rxn.bounds                               # (lower, upper)
rxn.gene_reaction_rule                   # GPR boolean logic, e.g. "b1723 or b3916"
model.metabolites.atp_c.formula          # "C10H12N5O13P3"
model.summary()                          # objective, top uptakes/secretions
```

## Flux Balance Analysis (FBA)

```python
solution = model.optimize()
solution.objective_value                 # e.g. growth rate
solution.status                          # MUST check: "optimal" vs "infeasible"
solution.fluxes["PFK"]                   # pandas Series of all reaction fluxes

model.objective = "ATPM"                 # retarget the objective by reaction ID
```

Variants (all in `cobra.flux_analysis`):

```python
from cobra.flux_analysis import pfba, geometric_fba
pfba(model)             # parsimonious FBA: min total flux at optimal objective
geometric_fba(model)    # a unique, central point in the optimal flux space
```

Standard FBA has *many* alternative optima, so a single `optimize()` flux vector is
not unique — use pFBA/geometric FBA or FVA/sampling when the distribution matters.

## Flux Variability Analysis (FVA)

```python
from cobra.flux_analysis import flux_variability_analysis
fva = flux_variability_analysis(model, fraction_of_optimum=0.9)   # DataFrame: minimum, maximum
flux_variability_analysis(model, loopless=True)                   # drop thermodynamically infeasible loops
flux_variability_analysis(model, reaction_list=["PFK", "FBA"], processes=4)
```

`fraction_of_optimum` sets how much objective you insist on keeping (1.0 = strictly
optimal). Loopless FVA is slower but removes internal-cycle artifacts.

## Gene and Reaction Knockouts

```python
from cobra.flux_analysis import single_gene_deletion, double_gene_deletion
single_gene_deletion(model)                       # DataFrame: ids, growth, status
double_gene_deletion(model, processes=4)          # parallelize — combinatorial cost
```

For one-off, temporary perturbations use the **context manager** — the model reverts
automatically on block exit:

```python
with model:
    model.genes.b0008.knock_out()                 # or model.reactions.PFK.knock_out()
    print(model.slim_optimize())                  # growth after knockout
# original state restored here
```

Essentiality helpers: `find_essential_genes(model, threshold=0.01)`,
`find_essential_reactions(...)`. Full knockout-screen script (classification,
synthetic lethals, plots) is in `references/workflows.md`.

## Growth Media and Minimal Media

`model.medium` is a dict of `{exchange_reaction_id: max_uptake}`. It is a computed
view — mutate a copy and reassign the whole dict:

```python
medium = model.medium
medium["EX_glc__D_e"] = 10.0     # glucose uptake cap (mmol/gDW/h)
medium["EX_o2_e"] = 0.0          # anaerobic
model.medium = medium

from cobra.medium import minimal_medium
minimal_medium(model, 0.1)                                  # min total import flux
minimal_medium(model, 0.1, minimize_components=True)        # fewest components (MILP, slower)
```

## Flux Sampling

```python
from cobra.sampling import sample
samples = sample(model, n=1000, method="optgp", processes=4)   # DataFrame, one column per reaction
# method="achr" is the serial alternative
```

Always validate for numerical stability before trusting a sample set — see the
`OptGPSampler.validate(...)` pattern in `references/api-reference.md`.

## Production Envelopes and Strain Design

```python
from cobra.flux_analysis import production_envelope
production_envelope(
    model,
    reactions=["EX_glc__D_e"],
    objective="EX_ac_e",            # e.g. acetate production
    carbon_sources="EX_glc__D_e",   # enables carbon-yield columns
)
```

The returned DataFrame (min/max objective and yields vs the control reaction) is the
phenotype phase plane. The complete strain-design loop — constrain growth, retarget
to product, screen knockouts for improvement, combine hits — is in
`references/workflows.md`.

## Gapfilling and Model Building

```python
from cobra.flux_analysis import gapfill
# There is no bundled "universal" model — supply your own candidate-reaction
# database (a downloaded BiGG universal model, or one you build).
universal = read_sbml_model("universal_reactions.xml")
gapfill(model, universal)            # returns reactions to add so the model grows

from cobra import Model, Reaction, Metabolite
```

Building a model from scratch (metabolites → reaction with stoichiometry and GPR →
`add_reactions` → `add_boundary` → set objective) is a mechanical sequence detailed
in `references/api-reference.md`.

## Core Mental Model

- **Bounds define reversibility.** Irreversible: `lower=0`. Reversible: `lower<0`. Set `reaction.bounds = (lo, hi)` together to avoid transient inconsistency.
- **Exchange reactions** (`EX_` prefix) are the system boundary. Negative flux = uptake, positive = secretion. Managed through `model.medium`.
- **GPR rules** map genes to reactions with boolean logic (`and` = complex/all-required, `or` = isozymes/any-sufficient); `knock_out()` respects them.
- **Context managers** (`with model:`) are the safe way to make temporary edits — they snapshot and roll back. Prefer them over manual save/restore.

## Failure Modes and Fixes

- **`status != "optimal"`** — never read `objective_value` without checking status first; an infeasible solve returns nonsense.
- **Infeasible model** — usually over-restrictive medium or bad bounds. Open all exchanges to isolate medium vs structural problems; check `find_blocked_reactions` and mass balance.
- **Unbounded objective** — an exchange or internal loop lets flux run to infinity; verify upper bounds and try `loopless=True`.
- **Slow FVA / deletions / sampling** — raise `processes`, or switch `model.solver` to `"cplex"` / `"gurobi"` if licensed.
- **Medium edits do nothing** — you mutated `model.medium` in place without reassigning; you must set `model.medium = medium`.

A full validation-and-debugging script (feasibility, mass/charge balance, dead-end
metabolites, duplicate reactions, orphan genes, loop detection) is in
`references/workflows.md`.

## References

- `references/api-reference.md` — signatures, parameters, model/reaction/metabolite/gene attributes, and reusable patterns.
- `references/workflows.md` — five complete workflows: knockout study, media design, flux-space exploration, strain design, model validation.
- Official docs: https://cobrapy.readthedocs.io/en/latest/
