---
name: diffdock
version: 0.1.0
description: >-
  Predict 3D protein-ligand binding poses with DiffDock, a diffusion generative
  model for blind molecular docking. Takes a protein (PDB file or amino-acid
  sequence via ESMFold) plus a ligand (SMILES or SDF/MOL2) and returns ranked
  poses, each with a confidence score, for single complexes, batch runs, or
  virtual screening. Use to answer "where and how does this molecule bind",
  generate docked poses for structure-based drug design, or screen a compound
  library against a target — especially with no known pocket, since DiffDock is
  blind/pocket-free. Do NOT use to predict binding affinity/ΔG/Kd (poses only —
  rescore with `binding-affinity`), for protein-protein docking (DiffDock-PP /
  AlphaFold-Multimer), covalent docking, large peptide ligands (>~20 residues),
  or membrane-protein targets. Confidence measures pose certainty, NOT binding
  strength.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "DiffDock MIT"
---

# DiffDock: Diffusion-Based Molecular Docking

## Overview

DiffDock casts molecular docking as a generative diffusion process over ligand
pose space: it starts from a randomly placed ligand and iteratively denoises its
position, orientation, and torsion angles onto the protein. It is a **blind**
docker — it searches the whole receptor surface and does not need a
pre-specified pocket — and it is state-of-the-art for pose prediction in
structure-based drug design.

Give it a protein (PDB file, or a sequence it folds with ESMFold) and a ligand
(SMILES or a structure file). It returns several ranked poses per complex, each
tagged with a **confidence score** that reflects how certain the model is that
the pose is near-native.

The one distinction to keep straight: DiffDock predicts **pose** (3D geometry)
and **confidence** (certainty), NOT **affinity** (ΔG, Kd). High confidence means
the model trusts the geometry, not that binding is strong. Rank affinity with a
separate scoring step (`binding-affinity`, GNINA, MM/GBSA, FEP).

## When to Use This Skill

- "Dock this ligand to this protein" / "predict the binding pose."
- "Where does this molecule bind?" with no known pocket (blind docking).
- Generate docked poses for structure-based design or lead optimization.
- Virtual screening: dock a compound library against one target and triage by
  confidence.
- Batch docking of many protein-ligand pairs.
- You have a sequence but no structure — DiffDock folds it with ESMFold first.

## When NOT to Use This Skill

- **Binding affinity / ΔG / Kd / ranking by potency** — DiffDock outputs poses,
  not energies. Rescore with `binding-affinity`, GNINA, MM/GBSA, or FEP.
- **Protein-protein or large-complex docking** — use DiffDock-PP,
  AlphaFold-Multimer, or RoseTTAFold2NA.
- **Large peptide/protein ligands (>~20 residues)**, **covalent docking**, or
  **membrane-protein targets** — outside DiffDock's training scope.
- **Finding the pocket as the deliverable** — DiffDock localizes the ligand as a
  by-product, but for explicit pocket detection use a dedicated cavity finder.
- **Generating new molecules** — design candidates elsewhere, then dock them here.

## Install

```bash
git clone https://github.com/gcorso/DiffDock.git && cd DiffDock
conda env create --file environment.yml && conda activate diffdock
```

Docker (`rbgcsail/diffdock`), cloud-GPU (Modal), and first-run notes are in
[references/workflows.md](references/workflows.md). A GPU is effectively
required (10–100× over CPU); the first run spends ~2–5 min building SO(2)/SO(3)
lookup tables, and ~500 MB of checkpoints download automatically.

## Single docking

```bash
python -m inference \
  --config default_inference_args.yaml \
  --protein_path protein.pdb \
  --ligand "CC(=O)Oc1ccccc1C(=O)O" \
  --out_dir results/single/
```

Output: ranked SDFs `rank1.sdf`, `rank2.sdf`, … ordered by descending
confidence, with the confidence value in each filename. `rank1` is the model's
best guess. Swap `--protein_path` for `--protein_sequence "MSK..."` to fold from
sequence, or point `--ligand` at an `.sdf`/`.mol2` file.

## Batch docking & virtual screening

Provide a CSV with columns `complex_name,protein_path,ligand_description,protein_sequence`
(leave the unused side of each row empty):

```bash
python -m inference --config default_inference_args.yaml \
  --protein_ligand_csv complexes.csv --out_dir results/batch/ --batch_size 10
```

Each complex writes to its own subdirectory. For a library against **one**
target, pre-compute the protein's ESM embedding once and pass
`--esm_embeddings_path` to skip re-embedding per ligand. Full screening,
ensemble (multi-conformation), and result-ranking recipes are in
[references/workflows.md](references/workflows.md).

## Tuning

- `--samples_per_complex` (default 10): raise to 20–40 for hard cases (large or
  flexible ligands, ambiguous pockets). More samples = better coverage, slower.
- `--inference_steps` (default 20): 25–30 can improve accuracy at higher cost.
- `--temp_sampling_tor` (default 7.04): raise (8–10) for flexible ligands, lower
  (5–6) for rigid ones.
- `--batch_size`: lower it (e.g. 2) on GPU out-of-memory.

Every flag, default, and the temperature/checkpoint tables are in
[references/parameters.md](references/parameters.md).

## Reading the confidence score

| Score | Level | Reading |
|-------|-------|---------|
| `> 0` | High | Top pose likely near-native. |
| `-1.5`–`0` | Moderate | Reasonable; inspect and validate. |
| `< -1.5` | Low | Uncertain; treat as a hypothesis. |

Expect lower confidence for large ligands (>500 Da), many-chain complexes, and
novel folds. Review the top 3–5 poses and look for consensus rather than trusting
a single rank-1. Confidence is certainty, **not** affinity. Calibration,
validation strategy, scope boundaries, and troubleshooting live in
[references/confidence-and-limitations.md](references/confidence-and-limitations.md).

## After docking: rescore for affinity

DiffDock stops at poses. To rank *binding strength*, feed the poses into a
scoring step — GNINA (fast), MM/GBSA (moderate), or FEP/TI (most accurate).
Recommended chain: DiffDock poses → visual inspection → affinity rescore →
experimental assay. The `binding-affinity` skill packages the rescoring step; see
[references/workflows.md](references/workflows.md) section 6 for a GNINA example.

## Related Skills

- `binding-affinity` — rescore DiffDock poses to estimate pKd/ΔG. DiffDock gives
  geometry; this gives the affinity ranking DiffDock cannot.
- `rdkit` — canonicalize/validate ligand SMILES and prepare structure files
  before docking.
- `esm` — protein language-model embeddings; DiffDock uses ESM2 for the receptor
  and ESMFold for sequence-only inputs.
- `deepchem` — broader ML-for-chemistry toolkit for downstream modeling.

## Citation

- Corso et al. (2023) "DiffDock: Diffusion Steps, Twists, and Turns for Molecular
  Docking," ICLR 2023, arXiv:2210.01776.
- Stärk et al. (2024) "DiffDock-L: Improving Molecular Docking with Diffusion
  Models" (current default checkpoint), arXiv:2402.18396.
- Code: https://github.com/gcorso/DiffDock · Demo:
  https://huggingface.co/spaces/reginabarzilaygroup/DiffDock-Web
</content>
