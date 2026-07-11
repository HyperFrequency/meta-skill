---
name: molecular-optimization
version: 0.1.0
description: >-
  Iterative lead optimization for small molecules: take a hit SMILES and improve
  its ADMET / physicochemical liabilities (LogP, hERG, TPSA, MW, QED, solubility)
  while preserving scaffold and potency, via an analyze → identify-liabilities →
  generate → verify → score → iterate loop. Candidates come from bioisosteric
  replacement (RDKit ReplaceSubstructs); every one is verified — valid SMILES,
  Murcko-scaffold match, ECFP4 Tanimoto, and a check that the CLAIMED modification
  actually exists in the structure — then ranked by net liability improvement.
  Method follows MT-Mol, DrugR, and MultiMol. Use to optimize a lead, do
  property-driven analog design, scaffold-hop, or balance multiple objectives. Do
  NOT use for de novo generation from scratch (use `denovo-design`), raw property
  prediction without optimization (use `admet-prediction`), liability
  interpretation only (use `admet-reasoning`), docking or affinity (use
  `molecular-docking`, `binding-affinity`), or for biologics, peptides, or
  PROTACs.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (RDKit)"
---

# Molecular Optimization

## Overview

Lead optimization is the slow middle of drug discovery: you have a hit that
works, and you must nudge its properties — lower LogP, kill an hERG risk, shave
molecular weight, lift QED — without breaking the pharmacophore that made it a
hit. Language models are bad at this unaided; they emit invalid SMILES and
"improvements" that don't correspond to any real atom of the input structure.

This skill runs optimization as a closed, verifiable loop instead of one-shot
generation:

**Analyze → Identify liabilities → Generate candidates → Verify → Score & rank → Iterate.**

Each modification is *generated* by a structural rule (bioisosteric replacement,
functional-group edit, ring/chain change) and then *checked against the actual
molecule* before it counts — that verification gate is what separates this from
blind prompting. The method distills three peer-reviewed approaches:

- **MT-Mol** (Kim et al., 2025) — multi-agent tool-based reasoning with an
  explicit verifier step. SOTA on 17/23 PMO benchmark tasks.
- **DrugR** (Liu et al., 2026) — reason about liabilities *before* generating,
  reporting a large improvement over blind generation.
- **MultiMol** (Yu et al., 2025) — generate-then-rank with scaffold preservation.

**This file is a router.** Depth lives in `references/`:

- `references/optimization-protocol.md` — the full six-step loop, ADMET
  threshold table, severity ordering, the bioisostere library, the net-score
  rule, iteration/stopping logic, and batch handling.
- `references/verification.md` — SMILES validation, Murcko-scaffold matching,
  ECFP4 Tanimoto, MCS, the claimed-modification checker, and the exact RDKit
  calls each uses.
- `references/reference-implementation.md` — a runnable, dependency-light RDKit
  reference (single molecule + batch CSV) that emits the JSON report.

## When to Use This Skill

- **Lead optimization.** Improve the ADMET profile of a hit while keeping its
  core scaffold and similarity to the parent.
- **Property-driven analog design.** Generate analogs aimed at a specific target
  (`LogP < 3`, `hERG < 0.3`, `QED > 0.5`) and rank them.
- **Scaffold hopping.** Explore replacements that keep key pharmacophoric
  features while changing the ring system (loosen the scaffold-match gate).
- **Multi-objective optimization.** Trade several properties at once and score
  the net effect rather than optimizing one in isolation.
- **Vetting a proposed edit.** You (or another model) claim "added a hydroxyl at
  the para position" — confirm the proposed SMILES actually reflects that.

## When NOT to Use This Skill

- **De novo design from scratch** (no starting hit) — use `denovo-design`. This
  skill *modifies* an existing molecule and penalizes drifting too far from it.
- **Raw property prediction with no optimization** — use `admet-prediction` to
  score a molecule; this skill calls that kind of scoring inside its loop.
- **Liability interpretation only** — to explain *why* a feature is a risk and
  what mechanism drives it, use `admet-reasoning`; it supplies the reasoning
  that steers this loop but does not run generation.
- **Docking / binding affinity** — use `molecular-docking` and
  `binding-affinity`. This skill optimizes ligand properties, not binding pose
  or ΔG.
- **Biologics, peptides, PROTACs, inorganics** — the descriptors, scaffolds, and
  bioisostere rules assume drug-like small molecules and are out of domain.

## The Loop in Brief

Run these steps; see `references/optimization-protocol.md` for the full detail.

1. **Analyze.** Parse the input with `Chem.MolFromSmiles`; abort on `None`.
   Compute descriptors (MW, LogP, TPSA, HBA, HBD, rotatable bonds, aromatic
   rings, QED, ring count) and the generic Murcko scaffold.
2. **Identify liabilities.** Flag every descriptor outside its ADMET target
   band and sort by severity (critical → high → medium → low). If nothing is
   flagged, stop — the molecule is already in range.
3. **Generate candidates.** Apply structural rules to the most severe
   liabilities — bioisosteric replacement (phenyl→pyridine, Cl→F,
   amide→sulfonamide, …) via `AllChem.ReplaceSubstructs`, plus group and
   ring/chain edits. Aim for 4–8 candidates per iteration.
4. **Verify.** For each candidate, discard anything `Chem.MolFromSmiles` cannot
   parse; require an ECFP4 Tanimoto to the parent above the optimization
   threshold (default 0.4 — below that it is de novo design, not optimization);
   check Murcko-scaffold preservation; and confirm the intended modification is
   actually present. Verification detail in `references/verification.md`.
5. **Score & rank.** Recompute descriptors, re-derive liabilities, and score by
   net improvement: **+1 per liability fixed, −0.5 per new liability
   introduced**. Sort descending.
6. **Iterate.** Adopt the top candidate as the new parent and repeat. Stop after
   `max_iterations` (default 3) or when an iteration yields no positive-scoring
   candidate. Return the best molecule found — and, if none beat the input, say
   so honestly rather than inventing an "improvement".

## Why Verification Is the Load-Bearing Step

The single most common failure of LLM-driven molecular design is a fluent,
confident answer that is chemically false: an unparseable SMILES, or a valid
SMILES whose structure does not contain the change the model just described. The
loop treats every generated candidate as a *claim* and refuses to score it until
RDKit confirms three things — it parses, it stays close to the parent (Tanimoto
+ scaffold), and the specific edit is really there. Skipping this gate is how a
pipeline produces "optimized" molecules that cannot be synthesized or that
silently abandoned the scaffold. Never report a candidate you have not verified.

## References

- `references/optimization-protocol.md` — full protocol, thresholds,
  bioisosteres, scoring, stopping, batch mode.
- `references/verification.md` — validation, similarity, scaffold, MCS,
  claimed-modification checks, RDKit API.
- `references/reference-implementation.md` — runnable RDKit reference code.

## Related Skills

- `admet-prediction` — computes the ADMET / drug-likeness properties this loop
  optimizes against.
- `admet-reasoning` — maps each liability to structural cause, mechanism, and
  fix; use it to choose *which* modification to make.
- `smiles-validation` — strict standalone SMILES parsing and structural checks.
- `denovo-design` — generation without a starting hit.
- `molecular-docking`, `binding-affinity` — pose generation and binding-strength
  estimation, downstream of property optimization.
