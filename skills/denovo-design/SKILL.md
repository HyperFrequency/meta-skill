---
name: denovo-design
version: 0.1.0
description: >-
  Generate novel drug-like molecules de novo with RDKit-based cheminformatics on
  CPU: scaffold analog enumeration (R-group scanning, bioisostere swaps, random
  graph mutation), fragment growing/linking/merging, structure-based design
  against a protein pocket (shape + pharmacophore heuristics), iterative
  multi-objective property optimization, and drug-likeness filtering (Lipinski,
  Veber, QED, PAINS, Brenk, lead/fragment-like, bRo5, SA proxy). Use when you
  have a lead compound, fragment hits, a target pocket, or a raw compound library
  and want to expand or triage chemical space fast without training a model. Not
  for deep generative models (VAE/diffusion/RL — see `deepchem`), physics-based
  docking or binding free energy (see `binding-affinity`), retrosynthesis
  planning, or standardizing/validating existing SMILES.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "RDKit BSD-3-Clause"
---

# De Novo Molecule Design

## Overview

De novo design is the computational generation of new molecular structures with
desired properties. This skill is a CPU-first toolkit of five RDKit-driven
command-line scripts that each cover one design strategy: analog enumeration,
fragment-based design, structure-based design (SBDD), multi-objective
optimization, and drug-likeness filtering. Every generator emits a CSV with
computed physicochemical properties and similarity metrics so you can rank and
triage candidates immediately.

These are **rule-based cheminformatics heuristics**, not learned generative
models. They are fast, deterministic (seeded), dependency-light, and produce
chemically valid SMILES — but their output is raw exploration that always needs
medicinal-chemistry review. See [Important Caveats](#important-caveats).

## When to Use This Skill

- You have a **lead compound** and want analogs (R-group scan, bioisosteric
  replacement, random graph mutation) to explore nearby chemical space.
- You have **fragment screening hits** and want to grow one fragment, link two,
  or merge their pharmacophores into lead-sized molecules.
- You have a **protein structure / pocket** and want quick candidate molecules
  shaped or featured to complement it, as a CPU starting point before docking.
- You have **hit compounds** and want to iteratively push them toward property
  targets (QED, LogP, SA, MW, TPSA, HBD/HBA) under hard constraints.
- You have a **raw library** and want to annotate/triage it against standard
  medchem filters.

## When NOT to Use This Skill

- **Deep generative models** (VAE, GAN, diffusion, RL policy) — use `deepchem`
  or a dedicated generative library. These scripts do no learning.
- **Physics-based docking, poses, or binding free energy** — the SBDD
  `binding_score` here is a shape+feature heuristic, not docking. Use
  `binding-affinity` for scoring poses.
- **Retrosynthesis / route planning** — the `sa_score` is a complexity proxy,
  not a synthesis planner.
- **Validating, standardizing, or canonicalizing existing SMILES** — use `rdkit`
  or `datamol` directly.
- **Heavy property/objective optimization campaigns** — the built-in `optimize.py`
  is a lightweight mutation loop; for serious multi-objective work see
  `molecular-optimization`.

## Setup

```bash
pip install rdkit numpy          # core (RDKit provides the cheminformatics engine)
pip install biopython            # optional: better PDB parsing for SBDD
```

RDKit is the only hard requirement for four of the five scripts; `generate_sbdd.py`
additionally requires `numpy`. `biopython` improves PDB parsing but the SBDD
script falls back to a plain-text PDB line parser without it.

## Choosing a Strategy

| You have… | Script | Modes / key flags |
|-----------|--------|-------------------|
| A lead compound, want analogs | `scripts/generate_analogs.py` | `--strategy all\|rgroup\|bioisostere\|mutate` |
| Fragment hits | `scripts/generate_fragments.py` | `--mode grow\|link\|merge` |
| A protein pocket | `scripts/generate_sbdd.py` | `--method shape\|pharmacophore` |
| Hits to optimize | `scripts/optimize.py` | `--objectives`, `--constraints` |
| A library to triage | `scripts/filter.py` | `--filters lipinski,pains,…` |

Full flag reference, defaults, output columns, and the built-in substituent /
bioisostere / linker / seed-fragment libraries are in
[references/cli-reference.md](references/cli-reference.md).

## The Five Tools

Each script writes a CSV and prints a property-distribution summary. Canonical
one-liners below; see the CLI reference for every flag.

**1. Analog generation** — enumerate substituents, swap bioisosteres, or randomly
mutate the molecular graph of a lead.

```bash
python scripts/generate_analogs.py --smiles "c1ccc(NC(=O)c2ccccc2)cc1" \
  --output analogs.csv --num 50 --strategy all
```

**2. Fragment-based design** — grow one fragment, or link/merge two (link/merge
require ≥2 comma-separated fragments).

```bash
python scripts/generate_fragments.py --fragments "c1cc[nH]c1,c1ccccc1O" \
  --mode link --output linked.csv --num 50
```

**3. Structure-based design** — assemble pocket-complementary molecules from a
PDB. `--pocket-residues auto` auto-detects; slowest script (embeds 3D
conformers for shape scoring).

```bash
python scripts/generate_sbdd.py --protein target.pdb \
  --pocket-residues "ASP189,SER195,HIS57" --method shape \
  --output sbdd_hits.csv --num 100
```

**4. Multi-objective optimization** — iterate mutate → score → constrain → select.

```bash
python scripts/optimize.py --input hits.csv --objectives qed,logp,sa \
  --constraints "mw<500,logp<5,qed>0.5" --output optimized.csv --num-iterations 3
```

**5. Drug-likeness filtering** — annotate each molecule with pass/fail per filter.
Note: this **annotates, it does not drop rows** — post-filter on `pass_all == "pass"`.

```bash
python scripts/filter.py --input library.csv --output filtered.csv \
  --filters lipinski,veber,qed,pains,brenk,leadlike,fragmentlike,bro5,sa
```

## Recommended Pipeline

Generate broad → filter → optimize survivors. A concrete end-to-end recipe
(chaining outputs, deduplication, FBDD merging, feeding SBDD hits into medchem
filters) is in
[references/pipelines-and-caveats.md](references/pipelines-and-caveats.md).

1. Generate widely (`generate_analogs.py --strategy all`, or SBDD/fragments).
2. Triage with `filter.py`, then keep only `pass_all == "pass"` rows.
3. Optimize the survivors with `optimize.py` under hard constraints.
4. Hand the top ranked compounds to a chemist and to real docking /
   `binding-affinity` scoring.

## Important Caveats

- **Heuristics, not ML.** Analog/fragment/SBDD generation grow molecules by
  bonding library groups onto matched atoms. Output is chemically valid but often
  strained or unusual — always review.
- **`sa_score` is a proxy**, a complexity heuristic (rings, stereocenters, MW,
  rotatable bonds, ring fusion), not the Ertl–Schuffenhauer SAscore and not a
  synthesis check. Treat SA ≤ 5 as "probably tractable", not a guarantee.
- **SBDD `binding_score` is not docking** — it blends a pocket-fill shape ratio
  with pharmacophore feature complementarity. Use it only to rank candidates for
  downstream real docking.
- **`filter.py` keeps every input row** and only flags it. Downstream steps must
  filter on `pass_all`.
- **`optimize.py` silently ignores unknown constraint properties** and outputs
  every molecule it explored (ranked), not just the final population.

Full failure modes and troubleshooting: see
[references/pipelines-and-caveats.md](references/pipelines-and-caveats.md).

## References

- [references/cli-reference.md](references/cli-reference.md) — every flag,
  default, output-column schema, and built-in chemical library per script.
- [references/pipelines-and-caveats.md](references/pipelines-and-caveats.md) —
  end-to-end recipes, method limitations, and troubleshooting.
