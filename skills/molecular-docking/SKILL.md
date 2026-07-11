---
name: molecular-docking
version: 0.1.0
description: >-
  End-to-end structure-based molecular docking: clean and protonate a protein
  target, define or detect the binding pocket, embed and charge small-molecule
  ligands from SMILES/SDF, dock with AutoDock Vina (physics-based) or DiffDock
  (deep learning), fingerprint protein-ligand interactions with ProLIF, and rank
  poses by a combined score/interaction metric. Use when docking a ligand into a
  protein, running virtual screening over a compound library, detecting or
  characterizing a binding site, rescoring or analyzing existing poses, or doing
  structure-based lead optimization from a PDB structure plus SMILES. Do NOT use
  for rigorous binding free energy (use `binding-affinity`, MM/GBSA, or FEP), for
  protein-protein or covalent docking (use ClusPro/HDOCK or a covalent workflow),
  or for building a 3D protein structure from sequence (fold with AlphaFold or
  ESMFold first, then dock).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: >-
    AutoDock Vina (Apache-2.0); RDKit (BSD-3-Clause); Meeko (LGPL-2.1);
    ProLIF (Apache-2.0); Biopython (BSD-style); DiffDock (MIT); Open Babel (GPL-2.0)
---

# Molecular Docking

## Overview

Structure-based docking predicts how a small molecule binds a protein — the 3D
pose and a score that ranks it against alternatives. This skill routes the full
pipeline and leans on open libraries (Biopython, RDKit, Meeko, AutoDock Vina,
ProLIF) rather than any single workbench, so each stage runs independently or as
a chain.

Pipeline at a glance:

1. **Target preparation** — parse the PDB, select a chain, strip waters and
   unwanted heteroatoms, add hydrogens, write a docking-ready receptor.
2. **Pocket definition** — locate the binding site from a co-crystal ligand,
   cavity detection, or a manually specified box.
3. **Ligand preparation** — SMILES/SDF to 3D conformers, protonate at pH, assign
   partial charges, write PDBQT.
4. **Docking** — Vina (fast, box-based, physics scoring) or DiffDock (blind,
   deep learning) to generate ranked poses.
5. **Interaction analysis & ranking** — ProLIF interaction fingerprint, then a
   composite score that combines docking energy with interaction quality.

Each stage below is a short router; the concrete APIs, parameters, and failure
modes live in `references/`.

## When to Use This Skill

- "Dock this ligand to a protein" / "predict how this molecule binds."
- "Run a virtual screen of this compound library against a target."
- "Find or characterize the binding pocket / active site on this PDB."
- "Prepare / clean this PDB for docking" or "convert this to PDBQT."
- "Score or re-rank these docked poses" / "what interactions does this pose make."
- Structure-based lead optimization where the binding pose context matters.

## When NOT to Use This Skill

- **Rigorous binding affinity / ΔG** — docking scores rank, they do not measure
  free energy. Use `binding-affinity`, MM/GBSA, or FEP.
- **Protein-protein or protein-peptide docking** — use ClusPro, HDOCK, or
  AlphaFold-Multimer, not a small-molecule box.
- **Covalent docking** — needs a specialized reactive-warhead workflow.
- **No 3D structure yet** — fold the sequence with AlphaFold/ESMFold first, then
  dock the predicted model.
- **Property/ADMET filtering of hits** — hand off to `admet-prediction`.

## Stage 1 — Target preparation

Parse and clean the receptor with Biopython (`PDBParser`, a `Select` subclass to
drop `HOH` and non-cofactor `HETATM`, chain selection, `PDBIO` write). Biopython
does not add hydrogens — use `reduce`, Open Babel (`obabel -h`), or PDBFixer,
which also repairs missing atoms/residues. Convert to a rigid-receptor PDBQT with
Meeko's `mk_prepare_receptor.py`, AutoDockTools `prepare_receptor4.py`, or
`obabel rec.pdb -xr -O rec.pdbqt`. Full code and failure modes:
[references/preparation.md](references/preparation.md). See sibling `biopython`
for general structure handling.

## Stage 2 — Pocket definition

Vina needs a search box (center + size); DiffDock does not. Derive a box center
from a co-crystallized ligand (most reliable), from geometric cavity detection,
or from known residues in a viewer. Size the box to the ligand's longest
dimension plus ~8–10 Å. For an unknown site, either run blind DiffDock or a
whole-protein Vina box with high exhaustiveness. Detection methods, druggability
criteria, and how to turn a pocket into box coordinates:
[references/pocket-detection.md](references/pocket-detection.md).

## Stage 3 — Ligand preparation

With RDKit: `MolFromSmiles` → `AddHs` → `EmbedMolecule`/`EmbedMultipleConfs`
(ETKDGv3) → `MMFFOptimizeMolecule`. Assign the dominant protonation state at your
target pH (Open Babel `-p 7.4`, Dimorphite-DL) and partial charges (Gasteiger),
then write PDBQT with Meeko's `mk_prepare_ligand.py` (defines rotatable-bond
torsions). Strip salts and pick the largest fragment first. Batch a CSV
(`name,smiles`) for screening. Details, embedding failures, and tautomer handling:
[references/preparation.md](references/preparation.md). See siblings `rdkit` and
`smiles-validation`.

## Stage 4 — Docking

**AutoDock Vina** (physics, box-based) via its Python API:

```python
from vina import Vina

v = Vina(sf_name="vina")                    # or "vinardo", "ad4"
v.set_receptor("receptor.pdbqt")
v.set_ligand_from_file("ligand.pdbqt")
v.compute_vina_maps(center=[cx, cy, cz], box_size=[20, 20, 20])
v.dock(exhaustiveness=32, n_poses=20)       # 8 default; 16–32 for production
v.write_poses("poses.pdbqt", n_poses=10, overwrite=True)
print(v.energies())                         # kcal/mol per pose; more negative = better
```

**DiffDock** (deep learning, blind) when the pocket is unknown or you want a
pose without a box — separate repo (`gcorso/DiffDock`, needs PyTorch Geometric +
GPU). It returns poses ranked by a confidence score (higher/positive = better)
but no energy, so rescore with Vina or ProLIF for affinity ranking. Full Vina
API, box/exhaustiveness/flexible-residue tuning, scoring-function choice, and the
DiffDock invocation and confidence bands:
[references/docking-engines.md](references/docking-engines.md). For a
DiffDock-focused workflow, use sibling `diffdock`.

## Stage 5 — Interaction analysis & ranking

Fingerprint each pose's contacts with ProLIF (`plf.sdf_supplier` over the poses,
`plf.Molecule.from_rdkit` for the receptor, `Fingerprint().run_from_iterable`,
`to_dataframe`) to enumerate hydrogen bonds, hydrophobic contacts, π-stacking,
salt bridges, and halogen bonds. The receptor must carry explicit hydrogens or
H-bonds are missed. Then rank by a composite of normalized docking score and
interaction quality — a compound should score well **and** make meaningful
contacts, which suppresses scoring-function false positives. Geometric criteria,
score interpretation, consensus rescoring, and the ranking recipe:
[references/interaction-analysis.md](references/interaction-analysis.md).

## Common workflows

- **Single ligand:** prepare target → define pocket → prepare ligand → Vina dock
  → ProLIF analyze → inspect top pose.
- **Virtual screening:** prepare target once → batch-prepare the library →
  Vina dock all (exhaustiveness 16–32, 5–10 poses each) → fingerprint → composite
  rank → take top N for follow-up (hand hits to `admet-prediction`).
- **Rescoring existing poses:** skip docking; run ProLIF on external poses and
  re-rank, or Vina `score()`/`optimize()` on a single pose.

## Environment

Python 3.11 (RDKit wheels lag on newer versions; pin `numpy<2` for older RDKit).
Core: `rdkit`, `biopython`, `scipy`, `numpy<2`. Docking: `vina`, `meeko`
(Meeko ≥0.5 needs RDKit ≥2023; use `meeko<0.6` with older RDKit). Interactions:
`prolif` (pulls MDAnalysis). PDBQT/protonation: Open Babel (`obabel`, install
`openbabel-wheel` for reliable Gasteiger charges). DiffDock installs separately.
Verify: `python -c "from vina import Vina; import prolif; from rdkit import Chem"`.

## Related skills

`diffdock` (deep-learning docking deep dive), `binding-affinity` (rigorous ΔG),
`admet-prediction` (filter hits), `rdkit` / `biopython` (library-level detail),
`smiles-validation` (clean input structures), `molecular-optimization` and
`medchem` (design the next compound to dock).
