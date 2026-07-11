---
name: datamol
version: 0.1.0
description: >-
  Pythonic, high-level wrapper over RDKit for everyday cheminformatics in drug
  discovery. Use for SMILES/SELFIES/InChI conversion, molecule standardization
  and sanitization, batch descriptor and fingerprint computation, Tanimoto
  similarity, Butina clustering and diversity selection, Murcko scaffolds,
  BRICS/RECAP fragmentation, 3D conformer generation, molecule visualization,
  and reading/writing SDF/CSV/Excel (including remote S3/GCS) with built-in
  parallelization. Objects returned are native rdkit.Chem.Mol, so results stay
  fully RDKit-compatible. Reach for datamol when you want sensible defaults and
  terse pipelines over up to ~thousands of molecules. NOT for low-level control
  or custom sanitization/fingerprint parameters (use rdkit directly), NOT for
  proteins/macromolecules or quantum-chemistry energies, and NOT for the ML
  modeling step itself — featurize here, then train with scikit-learn / pytorch.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (datamol)"
---

# Datamol

## Overview

Datamol is a thin, opinionated Python layer over RDKit. It keeps the same object
model — every molecule is a native `rdkit.Chem.Mol` — but replaces RDKit's
verbose, multi-import call sites with short functions and sensible defaults, and
adds first-class batch parallelization plus modern I/O (pandas DataFrames,
remote files via `fsspec`).

This skill is a **router**. It gives you the quick-start path, a capability map,
and the non-obvious failure modes, then delegates deep API surface and worked
examples to `references/`. The canonical import is `import datamol as dm`, and
almost every workflow is: turn a string or file into `Mol` objects, drop the ones
that failed to parse, standardize, then featurize / analyze / visualize.

## When to Use This Skill

Trigger when the user wants to:
- Convert between SMILES, SELFIES, InChI, InChIKey, or SMARTS
- Standardize / sanitize a set of externally supplied structures
- Compute descriptors or fingerprints across a **library** (not one molecule)
- Score molecular similarity, cluster, or pick a diverse/representative subset
- Extract Bemis-Murcko scaffolds or fragment molecules (BRICS / RECAP / MMPA)
- Generate and analyze 3D conformers
- Render molecule grids or SAR figures
- Read/write SDF, SMILES, CSV, Excel, or Parquet — including from S3/GCS/HTTP
- Build a compact, readable drug-discovery pipeline with parallelism for free

## When NOT to Use This Skill

- **Low-level control / custom parameters.** When you need to tune sanitization
  operations, fingerprint generators, or aromaticity models precisely, call
  `rdkit` directly — datamol deliberately hides those knobs. See the `rdkit`
  skill.
- **Proteins, nucleic acids, macromolecules.** Datamol (like RDKit) targets small
  molecules; use a dedicated structural-biology toolkit (e.g. `biopython`).
- **Quantum-chemistry energies / accurate conformer energetics.** The bundled
  force fields (UFF/MMFF) are geometry cleanup, not QM.
- **The ML modeling step.** Datamol produces features; hand fingerprints or a
  descriptor DataFrame to `scikit-learn`, `pytorch-lightning`, etc.
- **Very large libraries where every function must stream.** Full-matrix
  operations (Butina clustering, `pdist`) build an N×N matrix — fine to ~1,000s,
  not 100,000s. See the scale note below.

## Install and Import

```bash
uv pip install datamol      # pulls RDKit as a dependency
```

```python
import datamol as dm
```

## Capability Map

Each row is an entry point; follow the reference link for signatures, parameters,
and worked examples.

| Task | Entry point | Depth |
|---|---|---|
| Parse / convert (SMILES, SELFIES, InChI, SMARTS) | `dm.to_mol`, `dm.to_smiles`, `dm.to_selfies`, `dm.to_inchikey` | `references/core-api.md` |
| Standardize / sanitize / fix | `dm.sanitize_mol`, `dm.standardize_mol`, `dm.fix_mol` | `references/core-api.md` |
| Fingerprints & similarity | `dm.to_fp`, `dm.pdist`, `dm.cdist` | `references/core-api.md` |
| Clustering & diversity picking | `dm.cluster_mols`, `dm.pick_diverse`, `dm.pick_centroids` | `references/core-api.md` |
| Descriptors (single + batch) | `dm.descriptors.compute_many_descriptors`, `...batch_compute_many_descriptors` | `references/descriptors-and-viz.md` |
| Visualization / SAR figures | `dm.viz.to_image`, `dm.viz.conformers`, `dm.viz.circle_grid` | `references/descriptors-and-viz.md` |
| File I/O (SDF/SMILES/CSV/Excel/remote) | `dm.read_sdf`, `dm.read_csv`, `dm.open_df`, `dm.to_sdf` | `references/io.md` |
| 3D conformers, clustering, SASA | `dm.conformers.generate`, `...cluster`, `...sasa` | `references/conformers.md` |
| Scaffolds & fragmentation | `dm.to_scaffold_murcko`, `dm.fragment.brics`, `...recap` | `references/fragments-and-scaffolds.md` |
| Reactions & toy datasets | `dm.reactions.apply_reaction`, `dm.data.freesolv` | `references/reactions-and-data.md` |
| Generic parallel map | `dm.parallelized(fn, inputs, n_jobs=-1, progress=True)` | `references/core-api.md` |

## Minimal Recipes

**Parse and always check for `None`:**

```python
mol = dm.to_mol("CCO")                 # ethanol; returns None on failure
if mol is None:
    raise ValueError("unparseable SMILES")   # guard before every use
```

**Standardize externally supplied structures (do this before featurizing):**

```python
mol = dm.standardize_mol(
    mol, disconnect_metals=True, normalize=True, reionize=True
)
# For a raw string in one shot: dm.standardize_smiles(smiles)
```

**Batch descriptors in parallel → a DataFrame:**

```python
desc_df = dm.descriptors.batch_compute_many_descriptors(
    mols, n_jobs=-1, progress=True     # n_jobs=-1 uses all cores
)   # columns: mw, clogp, n_lipinski_hbd, n_lipinski_hba, tpsa, n_rotatable_bonds, qed, fsp3, ...
```

**Fingerprint + pairwise Tanimoto distance:**

```python
fp = dm.to_fp(mol, fp_type="ecfp", radius=2)   # also: maccs, fcfp, atompair, topological
dist = dm.pdist(mols, n_jobs=-1)               # Tanimoto DISTANCE (1 - similarity)
```

**Cluster and pick a diverse subset (both return `(indices, mols)` tuples — unpack them):**

```python
cluster_indices, cluster_mols = dm.cluster_mols(mols, cutoff=0.2, n_jobs=-1)  # index + mol clusters
diverse_indices, diverse_mols = dm.pick_diverse(mols, npick=100)              # 100 spread-out molecules
```

**3D conformers (hydrogens are added internally by default):**

```python
mol_3d = dm.conformers.generate(mol, n_confs=50, rms_cutoff=0.5, minimize_energy=True)
n = mol_3d.GetNumConformers()
```

Extended, runnable pipelines — load → standardize → filter → cluster → visualize,
SAR series, virtual screening — live in the reference files linked above.

## Scale and Parallelization

- `n_jobs` is accepted across batch functions: `1` = sequential, `-1` = all cores,
  a positive int = that many workers. `progress=True` prints a bar on the batch ops.
- **Full-matrix operations do not scale.** `dm.cluster_mols` (Butina) and
  `dm.pdist` materialize an N×N distance matrix — comfortable to a few thousand
  molecules, not tens of thousands. For large sets prefer `dm.pick_diverse` /
  `dm.pick_centroids`, or fingerprint in datamol and cluster with an external
  scalable method.

## Failure Modes and Gotchas

- **Unchecked `None`.** `dm.to_mol` and the file readers yield `None` for
  structures that fail to parse/sanitize. Filter them (`[m for m in mols if m]`)
  before any batch step, or a single bad row poisons the pipeline.
- **Skipping standardization.** Salts, tautomers, mixed protonation states, and
  disconnected metals make similarity and descriptors inconsistent. Run
  `dm.standardize_mol(...)` on anything from an external source before comparing.
- **Distance vs similarity sign.** `dm.pdist` / `dm.cdist` return Tanimoto
  **distance** (`0` = identical, `1` = maximally different). Convert with
  `similarity = 1 - distance`; do not rank as if larger means more similar.
- **Clustering cutoff direction.** In `dm.cluster_mols`, `cutoff` is a distance
  threshold — smaller cutoff = tighter, more numerous clusters.
- **Selection functions return tuples.** `dm.cluster_mols`, `dm.pick_diverse`, and
  `dm.pick_centroids` each return `(indices, mols)`. Unpack them — iterating the raw
  return treats the two halves as items, not the clusters/picks you expected.
- **3D geometry needs hydrogens.** `dm.conformers.generate` adds them for you by
  default (`add_hs=True`); if you pre-strip hydrogens and disable that, geometries
  degrade. Embeddings are already seeded (`random_seed=19`, so runs reproduce);
  energy minimization is **off** by default — pass `minimize_energy=True` for a
  force-field cleanup pass.
- **Remote I/O needs the backend.** `s3://`, `gs://`, `az://` paths require the
  matching `fsspec` backend installed (`s3fs`, `gcsfs`, `adlfs`); otherwise the
  read/write raises an import/protocol error.
- **`freesolv` and friends are toy datasets.** `dm.data.*` sets are for testing
  and tutorials only — do not benchmark or draw scientific conclusions from them.

## References

- `references/core-api.md` — top-level namespace: conversions, standardization,
  fingerprints/similarity, clustering/diversity, DataFrame bridges, `dm.parallelized`.
- `references/io.md` — reading/writing SDF, SMILES, CSV, Excel, Parquet, MOL/PDB
  blocks, `open_df`/`save_df`, and remote `fsspec` paths.
- `references/descriptors-and-viz.md` — the `descriptors` module (single + batch,
  specialized counts, Lipinski/ADME filtering) and the `viz` module (grids,
  alignment, highlighting, conformer and circle-grid figures).
- `references/conformers.md` — 3D embedding methods (ETKDGv3), conformer
  clustering, RMSD, SASA, coordinate access.
- `references/fragments-and-scaffolds.md` — Bemis-Murcko + fuzzy scaffolds,
  BRICS/RECAP/MMPA fragmentation, scaffold splits for ML, fragment analysis.
- `references/reactions-and-data.md` — applying SMARTS reactions and the bundled
  toy datasets.

## Related Skills

- `rdkit` — the underlying toolkit; drop down to it for low-level control.
- `scikit-learn`, `pytorch-lightning` — train models on datamol features.
- `shap` — explain models built on datamol descriptors/fingerprints.
