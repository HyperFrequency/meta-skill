---
name: rdkit
version: 0.1.0
description: >-
  RDKit cheminformatics toolkit for fine-grained programmatic control over
  molecules in Python. Use when you need to parse or write chemical structures
  (SMILES, SMARTS, SDF, MOL, InChI, PDB), compute molecular descriptors (MW,
  LogP, TPSA, QED, 200+ others), generate fingerprints and Tanimoto/Dice
  similarity, run substructure/SMARTS searches, apply reaction transforms,
  generate 2D depictions or 3D conformers with force-field optimization,
  standardize/sanitize structures, or draw molecules. Reach for RDKit when you
  need low-level control, custom sanitization, or specialized cheminformatics
  algorithms. NOT for simple high-level pipelines better served by a thin
  wrapper like datamol; NOT for protein/macromolecular modeling (use a
  structural-biology toolkit); NOT for quantum-chemistry energies (use a QM
  package); and NOT for ML model training itself — RDKit only featurizes.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (RDKit)"
---

# RDKit Cheminformatics Toolkit

## Overview

RDKit is a mature open-source cheminformatics library with a Python API for
reading, analyzing, transforming, and drawing small molecules. This skill is a
**router**: it gives you the quick-start path, a capability map, and the
non-obvious failure modes, then delegates deep API surface and pattern libraries
to `references/`. Use it for drug discovery, computational chemistry, and
featurization tasks where you need explicit control over sanitization,
descriptors, fingerprints, substructure logic, or 3D geometry.

The central object is a `Chem.Mol`. Almost every workflow is: parse a string or
file into a `Mol`, verify it is not `None`, then call analysis / transform / draw
functions on it.

## When to Use This Skill

Trigger when the user wants to:
- Parse or convert structures between SMILES, SMARTS, SDF/MOL, InChI, or PDB
- Compute descriptors (MolWt, LogP, TPSA, QED, Lipinski, Chi/Kappa, VSA, ...)
- Build fingerprints (Morgan/ECFP, RDKit topological, MACCS, atom-pair) and
  score molecular similarity or cluster a library
- Search for substructures / functional groups with SMARTS
- Enumerate products of a reaction SMARTS transform
- Generate 2D coordinates for depiction or 3D conformers with UFF/MMFF
- Standardize, neutralize, or canonicalize structures for a database
- Draw molecules, grids, or highlighted substructures to PNG/SVG

## When NOT to Use This Skill

- **Simple, high-level pipelines** where a thin RDKit wrapper (e.g. `datamol`)
  reads more cleanly — use RDKit directly only when you need the low-level knobs.
- **Proteins / nucleic acids / macromolecular structure** — RDKit handles small
  molecules; use a dedicated structural-biology toolkit for macromolecules.
- **Quantum-chemistry energies / accurate conformer energetics** — RDKit force
  fields (UFF, MMFF94) are geometry-cleanup tools, not QM; use a QM package.
- **Training ML models** — RDKit produces features/fingerprints; hand those to
  `scikit-learn`, `pytorch-lightning`, etc. for modeling.

## Install and Import

```bash
pip install rdkit          # modern wheels ("rdkit" on PyPI, 2022.09+)
# or: conda install -c conda-forge rdkit   # recommended for full extras
```

```python
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem, Descriptors, Draw, rdFingerprintGenerator
```

## Capability Map

Each row below is a short entry point; follow the reference link for signatures,
parameters, and worked examples.

| Task | Entry point | Depth |
|---|---|---|
| Read/write structures, batch SDF/SMILES | `Chem.MolFrom*` / `Chem.MolTo*` / `SDMolSupplier` | `references/workflows.md` |
| Sanitization & validation | `Chem.SanitizeMol`, `Chem.DetectChemistryProblems` | `references/workflows.md` |
| Descriptors & drug-likeness | `Descriptors.CalcMolDescriptors`, `Descriptors.qed` | `references/descriptors-reference.md` |
| Fingerprints & similarity | `rdFingerprintGenerator.GetMorganGenerator`, `DataStructs.TanimotoSimilarity` | `references/workflows.md` |
| Substructure / SMARTS search | `Chem.MolFromSmarts`, `mol.GetSubstructMatches` | `references/smarts-patterns.md` |
| Reactions | `AllChem.ReactionFromSmarts`, `rxn.RunReactants` | `references/workflows.md` |
| 2D depiction / 3D conformers | `AllChem.Compute2DCoords`, `AllChem.EmbedMolecule` | `references/workflows.md` |
| Drawing / highlighting | `Draw.MolToImage`, `rdMolDraw2D.MolDraw2DCairo` | `references/workflows.md` |
| Standardize / neutralize | `rdkit.Chem.MolStandardize.rdMolStandardize` | `references/workflows.md` |
| Full module-by-module API | — | `references/api-reference.md` |

## Minimal Recipes

**Parse and always check for `None`:**

```python
mol = Chem.MolFromSmiles("Cc1ccccc1")   # toluene
if mol is None:
    raise ValueError("unparseable SMILES")   # every MolFrom* can return None
```

**Descriptors + Lipinski Rule of Five:**

```python
mw, logp = Descriptors.MolWt(mol), Descriptors.MolLogP(mol)
hbd, hba = Descriptors.NumHDonors(mol), Descriptors.NumHAcceptors(mol)
druglike = mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10
# Descriptors.CalcMolDescriptors(mol) returns all ~210 as a dict.
```

**Morgan (ECFP-like) fingerprint + Tanimoto similarity** (modern generator API):

```python
gen = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
fp1, fp2 = gen.GetFingerprint(mol_a), gen.GetFingerprint(mol_b)
sim = DataStructs.TanimotoSimilarity(fp1, fp2)          # 0.0–1.0
# Bulk against a library: DataStructs.BulkTanimotoSimilarity(fp1, [fp2, fp3, ...])
```

**Substructure match with SMARTS:**

```python
patt = Chem.MolFromSmarts("C(=O)[OH]")        # carboxylic acid
mol.HasSubstructMatch(patt)                    # bool
mol.GetSubstructMatches(patt)                  # tuple of atom-index tuples
```

**3D conformer (add hydrogens first):**

```python
mh = Chem.AddHs(mol)                           # REQUIRED before embedding
AllChem.EmbedMolecule(mh, randomSeed=0xf00d)   # ETKDG
AllChem.MMFFOptimizeMolecule(mh)               # geometry cleanup
```

Extended, runnable versions of these — batch drug-likeness scan, similarity
screen, substructure/PAINS filter, clustering, reactions, drawing — live in
`references/workflows.md`.

## Failure Modes and Gotchas

- **Unchecked `None`.** Every `MolFrom*` returns `None` on a parse/sanitize
  failure (and prints to stderr). Guard before use, especially in loops over a
  library. Use `Chem.DetectChemistryProblems(mol)` on a `sanitize=False` parse to
  see why.
- **3D without hydrogens.** Call `Chem.AddHs(mol)` before `EmbedMolecule`;
  embedding on an implicit-H graph gives poor or failed geometries. `RemoveHs`
  afterward only if you do not need the coordinates.
- **Deprecated fingerprint calls.** `AllChem.GetMorganFingerprintAsBitVect(...)`
  still works but is deprecated; prefer `rdFingerprintGenerator.*` generators for
  new code and consistent count/bit vectors.
- **SMARTS matching semantics.** Unspecified query properties match anything; an
  aromatic query atom (`c`) will not match an aliphatic target atom (`C`) and vice
  versa; a charged query atom will not match an uncharged target. Test patterns on
  known positives/negatives — see `references/smarts-patterns.md`.
- **Kekulization / aromaticity errors.** Malformed aromatic rings raise on
  sanitize; parse with `sanitize=False` then inspect, or `Chem.Kekulize(mol,
  clearAromaticFlags=True)` when a writer needs explicit single/double bonds.
- **`MolSupplier` thread safety.** Supplier objects are not safe to share across
  threads. For large files use `ForwardSDMolSupplier` (streaming, low memory) or
  `MultithreadedSDMolSupplier`; for repeated loads, pickle the parsed `Mol` list
  to skip re-parsing.
- **2D vs 3D coordinates.** Depiction wants `Compute2DCoords`; geometry/pharma-
  cophore work wants an embedded 3D conformer. Generate the right one first.

## References

- `references/api-reference.md` — module-by-module API (I/O, atoms/bonds, rings,
  stereo, fingerprints, reactions, drawing, standardization) with signatures and
  key parameters, plus common enums (bond types, hybridization, sanitize ops).
- `references/descriptors-reference.md` — catalogue of `Descriptors` values grouped
  by family (physicochemical, topological, electronic, shape, VSA, drug-likeness)
  with batch-calculation and lead/drug-like filtering patterns.
- `references/smarts-patterns.md` — vetted SMARTS library for functional groups,
  ring systems/heterocycles, pharmacophore features, PAINS alerts, and SMARTS
  syntax notes.
- `references/workflows.md` — extended worked examples for I/O + batch, sanitization,
  similarity/clustering, conformers + force fields, drawing, reactions, and
  standardization.
