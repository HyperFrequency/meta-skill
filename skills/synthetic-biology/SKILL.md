---
name: synthetic-biology
version: 0.1.0
description: >-
  Design and simulate engineered biological systems with SciPy, python-libsbml,
  and Biopython. Codon-optimize genes for heterologous expression across
  E. coli / yeast / human / CHO — maximizing CAI while hitting a GC target and
  stripping restriction sites and homopolymer runs; simulate canonical gene
  circuits (repressilator oscillator, bistable toggle switch, inducible
  promoter) as growth-coupled ODEs and measure period, bistability, and
  fold-induction; build and validate SBML Level 3 models; sweep a parameter to
  locate saddle-node / bistable bifurcations; compute lineage fitness from
  barcode-sequencing counts; and design and annotate expression cassettes for
  genome insertion. Use when designing a DNA construct in silico or simulating
  synthetic-circuit dynamics before the bench. NOT for constraint-based
  metabolic flux modeling (use `cobrapy`), general sequence/alignment or cloning
  simulation (use `biopython` or `molecular-cloning`), single-cell omics (use
  `scanpy` / `anndata`), or plotting (use `matplotlib`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (SciPy, NumPy, pandas); LGPL-2.1 (libSBML, via python-libsbml); Biopython License Agreement (MIT-style) / BSD-3-Clause; matplotlib (PSF-based, BSD-style)"
---

# Synthetic Biology: Design & Simulation

## Overview

This skill is a **router** for the computational design and simulation of
engineered biological systems, built on SciPy, python-libsbml, and Biopython.
It covers three families of task:

- **Design** DNA — codon-optimize a coding sequence for a target host and lay
  out annotated expression cassettes for genome insertion.
- **Simulate** gene circuits — integrate the canonical ODE architectures
  (repressilator, toggle switch, inducible promoter) with growth dilution, and
  map their steady-state / bifurcation behavior over a parameter.
- **Standardize & measure** — emit validated SBML Level 3 models for exchange
  with other tools, and reduce barcode-sequencing count data to per-lineage
  fitness.

Every result is a deterministic, inspectable computation — no network calls, no
proprietary design service. The body below is a capability map with one
runnable quick-start each; full model equations, function signatures, parameter
tables, and end-to-end recipes live in `references/`.

## When to Use This Skill

- You need to back-translate a protein (or re-optimize a gene) for expression in
  *E. coli*, yeast, human, or CHO cells, and want CAI, GC content, and
  synthesis-blocker checks reported.
- You want to simulate a synthetic gene circuit and quantify it — oscillation
  period, whether a toggle is bistable, or the fold-induction of an inducible
  promoter.
- You need to find where a circuit switches between mono- and bistable behavior
  as a parameter (repression strength, cooperativity) is swept.
- You want to export a reaction network as a standards-compliant SBML file for
  another simulator or a database.
- You have a barcode count table (lineage tracking / fitness screen) and want
  per-timepoint log2 fitness and lineage clusters.
- You are designing an expression cassette (promoter–RBS–CDS–terminator) and
  inserting it into a genome record with correct feature coordinates.

## When NOT to Use This Skill

- **Constraint-based / genome-scale metabolic flux modeling** (FBA, knockouts,
  flux sampling) — use `cobrapy`.
- **General sequence manipulation, alignment, BLAST, Entrez, phylogenetics** —
  use `biopython`; for protein language models use `esm`.
- **Wet-lab cloning simulation** — PCR, restriction digests, Golden Gate /
  Gibson assembly, CRISPR guide design — use `molecular-cloning`.
- **Single-cell / omics count matrices** — use `scanpy` / `anndata`.
- **General statistical testing or curve-fit inference** — use
  `statistical-analysis`; for growth-curve fitting and population/community
  dynamics use `microbial-dynamics`.
- **Making the figures** — this skill computes; hand plots to `matplotlib`.

## Setup

```bash
uv pip install scipy numpy pandas          # circuits, bifurcation, barcode fitness
uv pip install python-libsbml              # SBML model construction (import name: libsbml)
uv pip install biopython                   # expression-cassette design / annotation
```

The package is `python-libsbml` but the import is `import libsbml`. See
`references/sbml-models.md` for install caveats.

## Capabilities

### 1. Codon optimization

Back-translate a protein (or re-code a gene) into the host's preferred codons,
then enforce manufacturability constraints. The Codon Adaptation Index (CAI) is
the geometric mean of per-codon weights `w_i = f(codon) / f(most-used synonym)`.

```python
import numpy as np

def calculate_cai(dna, usage, codon_to_aa):
    """Geometric-mean CAI over coding codons for one organism's usage table."""
    logs = []
    for i in range(0, len(dna) - 2, 3):
        aa = codon_to_aa.get(dna[i:i+3])
        if not aa or aa == "*":
            continue
        syn = usage[aa]                                  # {codon: frequency}
        w = max(syn.get(dna[i:i+3], 1e-3), 1e-3) / max(syn.values())
        logs.append(np.log(w))
    return float(np.exp(np.mean(logs))) if logs else 0.0
```

The full pipeline — per-organism usage tables (E. coli / yeast / human / CHO),
optimal-codon back-translation, restriction-site removal (BsaI/BpiI), sliding-
window GC correction, homopolymer-run breaking, and a translation-preservation
check — is in `references/codon-optimization.md`.

### 2. Gene circuit simulation

Integrate the canonical circuits with `scipy.integrate.solve_ivp`. Each gene
contributes an mRNA and a protein equation; repression is a Hill function.

```python
import numpy as np
from scipy.integrate import solve_ivp

def toggle(t, y, a=6.0, n=2.5, K=1.0, dm=1.0, dp=0.2, b=0.2, leak=0.03):
    m1, m2, p1, p2 = y                                   # gene1 -| gene2, gene2 -| gene1
    return [a / (1 + (p2 / K)**n) + leak - dm * m1,
            a / (1 + (p1 / K)**n) + leak - dm * m2,
            b * m1 - dp * p1,
            b * m2 - dp * p2]

sol = solve_ivp(toggle, [0, 200], [0.1, 5, 0.1, 5], t_eval=np.linspace(0, 200, 1000))
p1, p2 = sol.y[2, -1], sol.y[3, -1]
print(f"p1={p1:.2f} p2={p2:.2f} -> {'Gene 1 ON' if p1 > p2 else 'Gene 2 ON'}")
```

The repressilator (6-ODE ring oscillator) and inducible promoter, all default
parameters and their meaning, solver-tolerance settings for stiff kinetics,
oscillation-period estimation (`find_peaks`), toggle steady-state search, and
fold-induction are in `references/gene-circuits.md`.

### 3. SBML model construction

Build a standards-compliant SBML Level 3 Version 2 model with python-libsbml —
compartments, species (by amount or concentration), reactions with kinetic laws
parsed from infix formulas, and local parameters — then validate and write.

```python
import libsbml
doc = libsbml.SBMLDocument(3, 2)
model = doc.createModel()
# ... add compartment, species, reaction, kinetic law (parseL3Formula) ...
doc.checkConsistency()
print("errors:", doc.getNumErrors())
libsbml.writeSBMLToFile(doc, "model.xml")
```

The full builder (`create_sbml_document`, `add_compartments`, `add_species`,
`add_reactions`), the checked-return idiom, unit definitions, and validation /
error-severity handling are in `references/sbml-models.md`.

### 4. Bifurcation analysis

Sweep a parameter, integrate to steady state at each value from many initial
conditions, and detect saddle-node bifurcations where the count of stable states
changes (mono- ↔ bistable). For the inducible circuit this yields a
dose-response curve and EC50.

```python
# sweep repression strength; count distinct steady states per value
states = find_all_steady_states_toggle(params)   # helper in references/
print("bistable" if len(states) >= 2 else "monostable")
```

The convergence-checked steady-state finder, parameter aliasing (`alpha` →
`alpha1`/`alpha2`), the bifurcation detector, and dynamic-range / EC50 readouts
are in `references/bifurcation-analysis.md`.

### 5. Barcode-sequencing fitness

Reduce a barcode × timepoint count table to per-lineage fitness: filter
low-abundance barcodes, normalize to relative frequency, take log2 fold change
vs a reference timepoint, then cluster fitness trajectories.

```python
fitness = analyze_barcode_fitness(counts, reference_timepoint="T0", min_reads=10)
clusters = cluster_lineage_fitness(fitness, n_clusters=5)   # Ward linkage
```

Both helpers, the pseudocount convention, and the interpretation of positive vs
negative fitness are in `references/barcode-and-cassettes.md`.

### 6. Expression cassette design

Assemble a promoter–RBS–CDS–terminator cassette as annotated `SeqFeature`s and
splice it into a genome `SeqRecord`, shifting downstream feature coordinates by
the insert length so the map stays correct. Writes GenBank.

```python
new_record = insert_expression_cassette(genome, cds_dna, locus_position=1200,
                                        gene_name="gfp")
```

The feature layout, coordinate-offset logic, translation qualifier, and GenBank
export are in `references/barcode-and-cassettes.md`.

## Best Practices

- **Always verify translation** after codon optimization — the re-coded DNA must
  translate to the exact input protein. The pipeline checks this; treat a
  mismatch as a hard failure, not a warning.
- **Check GC after optimizing.** Maximal-CAI codon choice can push GC outside
  40–60%, which hurts synthesis and expression; the GC-correction step trades a
  little CAI for manufacturability.
- **Keep the growth-dilution term** (`+ mu` on every degradation, or the
  `beta + gamma` form) in circuit ODEs — dividing cells dilute every
  intracellular species, and omitting it inflates steady-state levels.
- **Bistability needs many initial conditions.** A single trajectory finds one
  attractor; probe both high/low-biased and random starts, or you will report a
  bistable switch as monostable.
- **Validate every SBML model** with `checkConsistency()` before writing — the
  most common failures are missing units and unbalanced/undeclared species.
- **Filter barcodes by read count** (≥10 at the reference timepoint) before
  computing fitness; low-count lineages are dominated by PCR/sequencing noise.
- **Use a stiff solver** (`method="BDF"` or `"Radau"`) when a circuit with fast
  mRNA and slow protein dynamics integrates slowly or the solver reports
  "excess work"; tighten `max_step` before loosening tolerances.

## References

- `references/codon-optimization.md` — CAI theory, per-organism usage tables,
  the full optimize→restriction→GC→homopolymer pipeline, translation check.
- `references/gene-circuits.md` — repressilator / toggle / inducible ODEs, all
  parameters, solver settings, period, steady states, fold-induction.
- `references/bifurcation-analysis.md` — steady-state finder, parameter sweeps
  and aliases, saddle-node detection, dose-response / EC50.
- `references/sbml-models.md` — python-libsbml builder, units, kinetic-law
  parsing, validation, install caveats, common errors.
- `references/barcode-and-cassettes.md` — barcode fitness + clustering, and
  expression-cassette design / genome insertion / GenBank annotation.
