---
name: structure-prediction
version: 0.1.0
description: >-
  Predict a protein's 3D structure directly from its amino-acid sequence with ESMFold
  (Meta's single-sequence language-model folder) — no MSA, one GPU, seconds per chain —
  then read out per-residue pLDDT confidence, evaluate fold quality, batch-fold many
  sequences, and compare a model against an experimental reference (Cα-RMSD, TM-score,
  GDT-TS). Use when you hold a sequence but no experimental structure and need a fast
  structural hypothesis for a drug-target, a point mutant, or a docking/MD starting model,
  or to triage which sequences are worth a slower AlphaFold2 run. NOT for protein complexes
  or multimers, ligand/cofactor/metal modelling, conformational ensembles, sequences over
  ~800 residues, or when a UniProt entry already has a precomputed AlphaFold DB structure —
  look that up instead of folding from scratch.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: fair-esm / ESMFold (MIT); Biopython (BSD-style)
---

# Structure Prediction (ESMFold)

## Overview

ESMFold turns a raw amino-acid string into full-atom 3D coordinates in a single forward
pass of a protein language model — no multiple-sequence alignment (MSA), no template
search. That makes it seconds-per-chain instead of the minutes-to-hours AlphaFold2 spends
building alignments, and it fits on one GPU (~16 GB VRAM for chains up to ~400 residues).
The trade-off is accuracy: on hard targets with few homologs, ESMFold trails AlphaFold2 by
roughly 10-15 GDT-TS points, but on easy, homolog-rich targets the two are comparable.

Every prediction ships per-residue **pLDDT** confidence in the PDB B-factor column, so you
always know which parts of the model to trust. This skill covers the four things you do with
that: fold one sequence, fold a batch, evaluate a model's confidence and quality, and
compare a model against an experimental reference.

## When to Use This Skill

Reach for `structure-prediction` when you need to:

- **Fold a single sequence** into a 3D model when no experimental structure exists.
- **Batch-fold** many sequences (a mutant panel, a designed library, a proteome slice) and
  rank them by confidence.
- **Evaluate** a predicted PDB: mean/per-residue pLDDT, confidence tiers, rough secondary-
  structure content, and low-confidence (likely disordered) regions.
- **Compare** a prediction against a PDB reference via Cα-RMSD, TM-score, and GDT-TS.
- **Triage before AlphaFold2**: fold everything fast with ESMFold, then send only the
  low-confidence targets to a slower MSA-based run.

Trigger phrases: "predict/fold this protein", "structure from sequence", "run ESMFold",
"how confident is this model", "batch fold", "compare to the crystal structure".

## When NOT to Use This Skill

- **Complexes, multimers, homo-/hetero-oligomers** — ESMFold folds one chain only. Use
  AlphaFold-Multimer or Boltz/Chai-style co-folding instead.
- **Ligands, cofactors, metals, nucleic acids** — none are modelled; output is apoprotein.
- **Conformational ensembles / dynamics** — you get one static structure, not states.
- **Sequences beyond ~800 residues** — expect out-of-memory errors and degraded quality;
  split into domains or move to a sharded AlphaFold2 run.
- **A protein with a known UniProt accession** — check the AlphaFold DB first; a precomputed
  structure is instant and needs no GPU. Only fold from scratch if it is absent.
- **Inter-domain / inter-chain confidence questions** — ESMFold does not emit PAE. Use
  AlphaFold2 when you need pairwise error estimates.
- **Generative design, embeddings, inverse folding** — that is the broader `esm` toolkit,
  not this structure-prediction path.

## Prerequisites

```bash
pip install "fair-esm[esmfold]" "torch>=1.12" "biopython>=1.84" numpy
```

- Python 3.8+; PyTorch 1.12+ with CUDA strongly recommended (CPU works but is far slower).
- A CUDA GPU with ≥16 GB VRAM for chains up to ~400 residues; 32+ GB for 400-800.
- Optional: the external `TMalign` binary for exact TM-score/GDT-TS in comparison. Without
  it, fall back to a Biopython superimposition and the analytic TM-score approximation.

## Core API

ESMFold is loaded once and reused. `infer_pdb` returns a PDB string with pLDDT already
written into the B-factor field.

```python
import torch, esm

model = esm.pretrained.esmfold_v1()
model = model.eval().to("cuda")     # or .to("cpu")
model.set_chunk_size(128)           # trades speed for lower peak VRAM on long chains

sequence = "MKFLILLFNILCLFPVLAADNHGVS..."   # standard 20-letter alphabet
with torch.no_grad():
    pdb_string = model.infer_pdb(sequence)

open("predicted.pdb", "w").write(pdb_string)
```

Extract per-residue pLDDT from the B-factor of each Cα atom (mean pLDDT is your headline
quality number):

```python
import numpy as np
plddt = [float(l[60:66]) for l in pdb_string.splitlines()
         if l.startswith("ATOM") and l[12:16].strip() == "CA"]
print("mean pLDDT:", np.mean(plddt))
```

## Workflows

The four workflows share the model above. Concrete, copy-ready recipes — batch loop with
per-sequence OOM recovery, the evaluation report, and the full comparison math — live in
[`references/api-recipes.md`](references/api-recipes.md).

1. **Single predict** — one sequence → one PDB + pLDDT summary. Core API above.
2. **Batch predict** — parse multi-FASTA or a `name,sequence` CSV, fold one at a time to
   cap memory, catch OOM per row, write each PDB plus a `summary.csv` of length + mean
   pLDDT. See recipe.
3. **Evaluate** — parse a PDB with `Bio.PDB`, read pLDDT from B-factors, bucket into
   confidence tiers, estimate helix/sheet/coil from backbone dihedrals (Ramachandran
   approximation; DSSP is more accurate), and flag contiguous pLDDT < 50 regions. See recipe.
4. **Compare** — align two structures by Cα, superimpose, and report RMSD, TM-score, and
   GDT-TS. Prefer `TMalign` when installed; otherwise use the Biopython + analytic
   fallback. See recipe.

## Interpreting pLDDT

pLDDT is a 0-100 per-residue confidence (predicted lDDT). Quick guide:

| pLDDT   | Confidence | Trust                                                        |
|---------|-----------|---------------------------------------------------------------|
| > 90    | Very high | Atomic detail; OK for docking, binding-site, mutagenesis work |
| 70-90   | Confident | Backbone reliable; side-chain rotamers approximate            |
| 50-70   | Low       | Topology only; do not use residue-level detail                |
| < 50    | Very low  | Likely intrinsically disordered — the *flag* is the signal    |

A well-folded globular domain typically shows mean pLDDT > 70 with a high-confidence core
and low scores only at flexible loops and termini. Mean pLDDT < 50 across the whole chain
means disorder, an out-of-distribution sequence, or a chain too long for single-sequence
folding — not necessarily a bug. Deep tier interpretation, when to trust vs. distrust, and
how pLDDT/PAE/pTM compare to AlphaFold2 are in
[`references/confidence-metrics.md`](references/confidence-metrics.md).

## Limitations & Failure Modes

- **Single chain only** — no complexes, no oligomers.
- **~800-residue ceiling** — long chains OOM on typical hardware; `set_chunk_size` helps
  peak memory but not the fundamental limit. Catch `RuntimeError` containing "out of
  memory", call `torch.cuda.empty_cache()`, and retry shorter or on CPU.
- **No PAE** — inter-domain / inter-chain confidence is unavailable; ESMFold also does not
  expose pTM in the default pipeline.
- **pLDDT is informative, not perfectly calibrated** — the 50-70 band needs manual review.
- **Estimated secondary structure** — the built-in helix/sheet call is a dihedral
  approximation; use DSSP for anything quantitative.
- **Approximate TM-score without TMalign** — the fallback aligns by residue number, not by
  optimal structural superposition, so install `TMalign` for publication-grade numbers.
- **Non-standard residues / empty input** — validate against the 20-letter alphabet before
  folding; warn on unknowns, error on empty.

## Related Skills

- `esm` — generative protein design, embeddings, and inverse folding (superset of folding).
- AlphaFold2 / AlphaFold-Multimer — higher accuracy on hard targets, MSA-based, multimer and
  PAE support; the escalation target when ESMFold confidence is low.
- AlphaFold DB lookup — pull a precomputed structure by UniProt ID before folding anew.
