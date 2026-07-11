---
name: binding-affinity
version: 0.1.0
description: >-
  Predict protein-ligand binding affinity from docked poses, turning a complex
  into estimated pKd, ΔG (kcal/mol), and Kd. Covers empirical descriptor +
  contact scoring (RDKit/BioPython), physics-based MM/GBSA rescoring (OpenMM,
  with an RDKit MMFF fallback), rank-based multi-method consensus, and batch
  virtual screening. Use AFTER docking to rank poses, rescore a congeneric
  series, or prioritize a compound library for experimental testing. Do NOT use
  to find binding pockets (use `pocket-detection`), generate docked poses (use
  `molecular-docking`), predict drug-likeness/ADMET (use `admet-prediction`), or
  compute rigorous binding free energies (use alchemical FEP/TI, not covered
  here). All outputs are computational estimates with ~1-2 log-unit pKd error —
  good for RELATIVE ranking, never for absolute affinity or clinical claims.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "RDKit BSD-3-Clause; OpenMM MIT; Biopython BSD-style"
---

# Binding Affinity Prediction

## Overview

This skill estimates how tightly a ligand binds a protein, starting from a
docked pose (a protein-ligand complex) and producing binding strength in energy
units: predicted **pKd**, **ΔG** (kcal/mol), and **Kd** (nM). It sits downstream
of docking — interaction analysis counts contacts and hydrogen bonds but does
not estimate *strength*, and a raw docking score (e.g. Vina) is a coarse proxy.
Binding affinity prediction turns geometry into a ranked, comparable number.

Four complementary method families are covered, from a fast heuristic to a
physics-based rescorer to a consensus that combines them:

1. **Empirical descriptor + contact scoring** — RDKit ligand descriptors plus
   typed protein-ligand contacts, mapped to pKd. Fast, no MD.
2. **MM/GBSA rescoring** — molecular-mechanics energy with implicit-solvent
   (Generalized Born) via OpenMM; an RDKit MMFF path when OpenMM is absent.
3. **Consensus scoring** — rank-normalize several methods and measure their
   agreement (Kendall τ) for a more robust ordering.
4. **Batch virtual screening** — apply the fast empirical model across a library
   to shortlist compounds.

The methods, their accuracy, and how to build each one are in
[references/scoring-methods.md](references/scoring-methods.md) and
[references/implementation.md](references/implementation.md).

## When to Use This Skill

Reach for `binding-affinity` when you need to:

- Estimate how tightly a docked ligand binds (convert a pose to pKd / ΔG / Kd).
- Rank multiple docked poses or ligands by predicted affinity.
- Rescore poses with physics-based MM/GBSA for better relative ordering within a
  congeneric series.
- Combine docking score, empirical score, MM/GBSA, and interaction counts into a
  single consensus ranking.
- Screen a compound library to prioritize hits for experimental assays.

Trigger phrases: "predict binding affinity", "estimate Kd / pKd", "score binding
strength", "rescore with MM/GBSA", "rank compounds by affinity", "virtual
screening", "which pose binds tightest".

## When NOT to Use This Skill

- **Finding binding pockets** on an apo structure → use `pocket-detection`.
- **Generating docked poses** (you need poses *first*) → use `molecular-docking`.
- **Drug-likeness, permeability, tox, ADMET filtering** → use `admet-prediction`.
- **Rigorous absolute binding free energies** → alchemical free-energy methods
  (FEP/TI with explicit-solvent MD). MM/GBSA here is a ranking tool, not FEP.
- **Making quantitative or clinical claims** from a single predicted number. The
  gold standard is experiment (ITC, SPR, biochemical assay); this skill only
  prioritizes what to test.

## Predictions Are Estimates, Not Measurements

Every number this skill produces is a computational estimate:

- Empirical scoring: typical error is **1-2 log units of pKd** (~10-100× in Kd),
  Pearson r ≈ 0.5-0.6 against PDBbind. A predicted pKd of 7.2 means the true
  value is plausibly anywhere in ~5.7-8.7 (Kd ~2 nM to ~2 µM).
- MM/GBSA: useful for **relative** ranking within a series, not absolute ΔG. It
  omits configurational entropy (3-10 kcal/mol) and uses a single snapshot.
- Relative ranking is far more reliable than any single absolute value.

**Output integrity — do not launder the estimate:** report raw predicted
pKd/Kd/ΔG exactly as computed. Do **not** rescale or "calibrate" numbers to match
known experimental values, do not invent a `calibrated_pKd`, and do not present a
simplified MM/GBSA approximation as a full rigorous calculation. The raw estimate
*is* the prediction; carry its uncertainty and confidence flags forward.

## The Four Scoring Methods

| Method | Needs | Speed | Best for | Depth |
|--------|-------|-------|----------|-------|
| Empirical descriptor + contact | RDKit (+ BioPython) | fast | quick ranking, screening | [scoring-methods.md](references/scoring-methods.md) |
| MM/GBSA (OpenMM) | OpenMM + ligand params | slow | congeneric-series rescoring | [scoring-methods.md](references/scoring-methods.md) |
| MM/GBSA (RDKit MMFF fallback) | RDKit only | fast | very rough filtering | [scoring-methods.md](references/scoring-methods.md) |
| Consensus | ≥2 score sources | fast | robust final ranking | [scoring-methods.md](references/scoring-methods.md) |

Pick by budget and goal: no MD available → empirical only; careful study with
OpenMM → empirical + MM/GBSA + consensus; congeneric series → MM/GBSA; large
diverse library → empirical batch screen, then consensus with docking scores.
The full selection guide and per-method accuracy are in
[references/scoring-methods.md](references/scoring-methods.md).

## Building the Pipeline

Typical order of operations (each stage feeds the next):

```
pocket-detection → molecular-docking → interaction analysis
                                            ↓
                    empirical affinity  →  MM/GBSA rescore
                                            ↓
                                   consensus ranking → shortlist
```

Concrete, copy-ready recipes using real library APIs — RDKit descriptor and
contact extraction, exact pKd↔ΔG↔Kd thermodynamic conversions, an OpenMM
Generalized-Born energy scaffold, the RDKit MMFF fallback, and a
`scipy.stats.kendalltau` consensus — are in
[references/implementation.md](references/implementation.md).

## Interpreting the Numbers (quick reference)

| pKd | Kd (approx) | Reading |
|-----|-------------|---------|
| > 9 | < 1 nM | very potent (clinical-candidate range) |
| 7-9 | 1-100 nM | potent (lead range) |
| 5-7 | 100 nM - 10 µM | moderate (hit range) |
| < 5 | > 10 µM | weak / fragment / non-binder |

More negative ΔG (and more negative MM/GBSA energy) = stronger predicted binding.
Always report the pKd uncertainty band and the applicability-domain **confidence**
(high / moderate / low), which flags molecules outside the drug-like domain (MW
200-600, LogP -1 to 5, ≥30 contacts). Full pKd, ΔG, MM/GBSA, and confidence
tables live in [references/scoring-methods.md](references/scoring-methods.md).

## Dependencies

- **Required:** `rdkit`, `numpy`, `scipy`; `biopython` (recommended for accurate
  PDB atom parsing, else RDKit parses the PDB).
- **Optional (MM/GBSA full path):** `openmm`, plus ligand parameterization
  (`openff-toolkit` / `openmmforcefields`). Without OpenMM, MM/GBSA degrades to
  the RDKit MMFF approximation.

Setup and verification commands are in
[references/implementation.md](references/implementation.md).

## Related Skills

- `molecular-docking` — generate the poses this skill scores; run it first.
- `pocket-detection` — locate the binding site before docking.
- `admet-prediction` — filter affinity hits by drug-likeness and safety.

## References

- Wang, R. et al. "The PDBbind database." *J. Med. Chem.* 47, 2977-2980 (2004).
- Ballester, P.J. & Mitchell, J.B.O. "A machine learning approach to predicting
  protein-ligand binding affinity." *Bioinformatics* 26, 1169-1175 (2010).
- Hou, T. et al. "Assessing the performance of the MM/PBSA and MM/GBSA methods."
  *J. Chem. Inf. Model.* 51, 69-82 (2011).
- Houston, D.R. & Walkinshaw, M.D. "Consensus docking." *J. Chem. Inf. Model.*
  53, 384-390 (2013).
