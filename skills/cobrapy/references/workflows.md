# COBRApy Workflows

End-to-end, adaptable scripts for the tasks the router `SKILL.md` names. Each is a
template — swap in your own model, reaction IDs, and thresholds. Plots use
`matplotlib` / `seaborn` (see the sibling skills of the same name); every COBRApy
result here is a pandas object that plots directly.

These scripts use the bundled `textbook` E. coli core model, so every reaction ID
is valid and they run offline as-is. Genome-scale models (`load_model("iJO1366")`)
have far more genes and use different biomass and exchange IDs — always confirm with
`model.reactions.query(...)` before hardcoding, and expect deletion/sampling runs to
take much longer.

---

## Workflow 1 — Gene Knockout Study

Classify genes by knockout impact, then hunt synthetic-lethal pairs among the
survivors.

```python
import pandas as pd
import matplotlib.pyplot as plt
from cobra.io import load_model
from cobra.flux_analysis import single_gene_deletion, double_gene_deletion

model = load_model("textbook")
baseline = model.slim_optimize()

single = single_gene_deletion(model)          # columns: ids, growth, status

essential   = single[single["growth"] < 0.01]
severe      = single[(single["growth"] >= 0.01) & (single["growth"] < 0.5 * baseline)]
moderate    = single[(single["growth"] >= 0.5 * baseline) & (single["growth"] < 0.9 * baseline)]
neutral     = single[single["growth"] >= 0.9 * baseline]

# Distribution of post-knockout growth
ax = single["growth"].hist(bins=50)
ax.axvline(baseline, color="r", linestyle="--", label="baseline")
ax.set_xlabel("growth (/h)"); ax.set_ylabel("genes"); ax.legend()
plt.savefig("single_deletion_hist.png", dpi=200)

# The `ids` column holds a frozenset per row (the deleted gene(s)); the DataFrame
# index is a plain RangeIndex, NOT the ids — so read genes off the `ids` column.
single_growth = {next(iter(row.ids)): row.growth for row in single.itertuples()}

# Synthetic lethals: pairs lethal together but tolerable alone.
# Restrict to single-gene-tolerable genes and cap the list — double deletion is combinatorial.
survivors = [gene for gene, growth in single_growth.items() if growth >= 0.5 * baseline][:50]
double = double_gene_deletion(model, gene_list1=survivors, processes=4)

def is_synthetic_lethal(row):
    pair = list(row.ids)                          # frozenset of the two deleted genes
    if len(pair) < 2:                             # skip self-pairs on the diagonal
        return False
    gene_a, gene_b = pair
    return (row.growth < 0.01                     # lethal together
            and single_growth[gene_a] >= 0.5 * baseline   # each tolerable alone
            and single_growth[gene_b] >= 0.5 * baseline)

synthetic_lethals = double[double.apply(is_synthetic_lethal, axis=1)]
synthetic_lethals.to_csv("synthetic_lethals.csv")
```

Key point: single-gene tolerance is a precondition for a *synthetic* lethal — the
per-gene check in `is_synthetic_lethal` is what makes the pair interesting rather than
just an essential gene dragging the pair down.

---

## Workflow 2 — Media Design and Minimal Media

Compute minimal media across growth targets, compare aerobic vs anaerobic
requirements, and find the limiting nutrient in a custom medium.

```python
from cobra.io import load_model
from cobra.medium import minimal_medium
import pandas as pd

model = load_model("textbook")
baseline = model.slim_optimize()

# Minimal media at several growth fractions
media = {}
for fraction in (0.25, 0.5, 0.75, 1.0):
    media[fraction] = minimal_medium(
        model, baseline * fraction, minimize_components=True, open_exchanges=True
    )
pd.DataFrame(media).fillna(0).to_csv("minimal_media.csv")

# Aerobic vs anaerobic requirement diff
aer = minimal_medium(model, baseline * 0.9, minimize_components=True)

anaerobic = model.copy()
m = anaerobic.medium; m["EX_o2_e"] = 0.0; anaerobic.medium = m
ana = minimal_medium(anaerobic, anaerobic.slim_optimize() * 0.9, minimize_components=True)

aerobic_only   = set(aer.index) - set(ana.index)
anaerobic_only = set(ana.index) - set(aer.index)

# Limiting-nutrient probe on a custom medium
# Only exchanges that exist in the model — an unknown id raises KeyError.
# (The textbook core model has no sulfate exchange; genome-scale models add EX_so4_e.)
custom = {"EX_glc__D_e": 10.0, "EX_o2_e": 20.0, "EX_nh4_e": 5.0, "EX_pi_e": 5.0}
with model:
    model.medium = custom
    base = model.optimize().objective_value
    for exchange in custom:
        with model:
            m = model.medium; m[exchange] *= 2; model.medium = m
            gain = (model.optimize().objective_value - base) / base * 100
            if gain > 1:
                print(f"{exchange}: +{gain:.1f}% when doubled (LIMITING)")
```

`minimize_components=True` triggers a MILP and is markedly slower than the default
min-total-flux objective — use it only when you actually want the smallest *count* of
ingredients.

---

## Workflow 3 — Flux-Space Exploration (FVA + Sampling)

FVA gives the reachable range per reaction; sampling gives the *distribution* inside
the polytope and the correlation structure between reactions.

```python
from cobra.io import load_model
from cobra.flux_analysis import flux_variability_analysis
from cobra.sampling import sample
import matplotlib.pyplot as plt
import seaborn as sns

model = load_model("textbook")

fva = flux_variability_analysis(model, fraction_of_optimum=1.0)
fva["range"] = fva["maximum"] - fva["minimum"]
flexible = fva[fva["range"] > 1.0].sort_values("range", ascending=False)

# Relaxing optimality opens up more flux freedom
fva90 = flux_variability_analysis(model, fraction_of_optimum=0.9)
opened = (fva90["maximum"] - fva90["minimum"]) - fva["range"]

samples = sample(model, n=1000, method="optgp", processes=4)

# Per-reaction distributions with FVA bounds overlaid
keys = [r for r in ["PFK","FBA","TPI","GAPD","PGK","PGM","ENO","PYK"] if r in samples.columns]
fig, axes = plt.subplots(2, 4, figsize=(16, 8)); axes = axes.flatten()
for ax, rid in zip(axes, keys):
    samples[rid].hist(bins=30, ax=ax, alpha=0.7)
    ax.axvline(fva.loc[rid, "minimum"], color="r", linestyle="--")
    ax.axvline(fva.loc[rid, "maximum"], color="r", linestyle="--")
    ax.set_title(rid)
plt.savefig("flux_distributions.png", dpi=200)

# Correlated reaction modules
corr = samples[keys].corr()
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True)
plt.savefig("flux_correlations.png", dpi=200)
for i in range(len(corr)):
    for j in range(i + 1, len(corr)):
        if abs(corr.iloc[i, j]) > 0.9:
            print(f"{corr.index[i]} <-> {corr.columns[j]}: {corr.iloc[i, j]:.3f}")
```

FVA and sampling answer different questions: FVA bounds the *extremes*, sampling
reveals where flux actually concentrates and which reactions co-vary. Use both.

---

## Workflow 4 — Production Strain Design

Retarget the model to a product, hold a minimum growth, and screen knockouts that
push production up.

```python
from cobra.io import load_model
from cobra.flux_analysis import production_envelope
import pandas as pd

TARGET  = "EX_ac_e"          # acetate secretion
CARBON  = "EX_glc__D_e"      # glucose uptake
BIOMASS = "Biomass_Ecoli_core"   # textbook core biomass; confirm the exact ID for your model
MIN_GROWTH = 0.1

model = load_model("textbook")

# Wild-type production envelope (phenotype phase plane)
env = production_envelope(model, reactions=[CARBON], objective=TARGET, carbon_sources=CARBON)

# Max production subject to a growth floor
model.reactions.get_by_id(BIOMASS).lower_bound = MIN_GROWTH
with model:
    model.objective = TARGET
    model.objective_direction = "max"
    base_prod = model.optimize().objective_value

# Screen single knockouts for >5% production gain (growth floor still enforced)
hits = []
model.objective = TARGET
model.objective_direction = "max"
for gene in model.genes:
    with model:
        gene.knock_out()
        sol = model.optimize()
        if sol.status == "optimal" and sol.objective_value > base_prod * 1.05:
            hits.append({"gene": gene.id,
                         "production": sol.objective_value,
                         "growth": sol.fluxes[BIOMASS],
                         "improvement_pct": (sol.objective_value / base_prod - 1) * 100})
hits = pd.DataFrame(hits).sort_values("improvement_pct", ascending=False)

# Stack the top hits and re-check (epistasis: combined gain is not additive)
if len(hits):
    with model:
        for gid in hits.head(3)["gene"]:
            model.genes.get_by_id(gid).knock_out()
        combo = model.optimize()
        print(f"combined production: {combo.objective_value:.3f}, growth: {combo.fluxes[BIOMASS]:.3f}")
```

The growth floor is what keeps the design biologically meaningful — without it the
optimizer will happily route all carbon to product and predict a dead cell. Combining
top single hits is a heuristic, not a guarantee; always re-optimize the combination.

---

## Workflow 5 — Model Validation and Debugging

Run before trusting a model you did not build: feasibility, mass balance, dead ends,
duplicates, orphan genes, and loops.

```python
from cobra.io import load_model
from cobra.flux_analysis import find_blocked_reactions, flux_variability_analysis

model = load_model("textbook")   # or read_sbml_model("your_model.xml")

# 1. Feasibility — and isolate medium vs structural infeasibility
obj = model.slim_optimize()
if obj is None or obj != obj:          # NaN => not optimal
    blocked = find_blocked_reactions(model)
    with model:
        for ex in model.exchanges:
            ex.lower_bound = -1000     # open everything
        if model.slim_optimize() > 0:
            print("infeasible due to restrictive MEDIUM")
        else:
            print("infeasible due to STRUCTURE (missing reactions / imbalance)")

# 2. Mass & charge balance
unbalanced = {r.id: r.check_mass_balance() for r in model.reactions if r.check_mass_balance()}

# 3. Dead-end metabolites (only produced or only consumed)
dead_ends = []
for met in model.metabolites:
    producers = [r for r in met.reactions if r.metabolites[met] > 0]
    consumers = [r for r in met.reactions if r.metabolites[met] < 0]
    if not producers or not consumers:
        dead_ends.append(met.id)

# 4. Duplicate reactions (identical equations)
seen, duplicates = {}, []
for r in model.reactions:
    eq = r.build_reaction_string()
    if eq in seen:
        duplicates.append((seen[eq], r.id))
    else:
        seen[eq] = r.id

# 5. Orphan genes (no reaction association)
orphans = [g.id for g in model.genes if len(g.reactions) == 0]

# 6. Thermodynamically infeasible loops — where loopless FVA narrows the range
std  = flux_variability_analysis(model)
loop = flux_variability_analysis(model, loopless=True)
loopy = [rid for rid in std.index
         if (std.loc[rid, "maximum"] - std.loc[rid, "minimum"])
            > (loop.loc[rid, "maximum"] - loop.loc[rid, "minimum"]) + 0.1]

print({"unbalanced": len(unbalanced), "dead_ends": len(dead_ends),
       "duplicates": len(duplicates), "orphans": len(orphans), "loopy": len(loopy)})
```

Read the checks in order: a model that is infeasible is not worth balance-checking
until it grows, and loop detection is the slowest step (two FVA passes) so run it last.

Adapt every threshold to your model's scale — a genome-scale reconstruction has
thousands of reactions and different numeric ranges than the E. coli core model.
