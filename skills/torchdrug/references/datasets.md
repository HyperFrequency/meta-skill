# Dataset Catalog

40+ built-in datasets in `torchdrug.datasets`, across molecules, proteins,
knowledge graphs, and reactions. All support automatic download, lazy loading, and
configurable feature extraction. Sizes are approximate and useful for planning,
not exact reproduction — confirm current numbers from the loader if a paper depends
on them.

## Molecular property — classification

| Class | Size | Labels | What it predicts |
|---|---|---|---|
| `BACE` | 1,513 | binary | β-secretase inhibition (Alzheimer's) |
| `BBBP` | 2,039 | binary | Blood-brain-barrier penetration |
| `HIV` | 41,127 | binary | Inhibition of HIV replication |
| `ClinTox` | 1,478 | 2 multi-label | Clinical-trial toxicity |
| `SIDER` | 1,427 | 27 multi-label | Side effects by organ class |
| `Tox21` | 7,831 | 12 multi-label | Toxicity across 12 targets |
| `ToxCast` | 8,576 | 617 multi-label | High-throughput toxicology |
| `MUV` | 93,087 | 17 multi-label | Unbiased virtual-screening validation |

Use scaffold splits; report AUROC + AUPRC; multi-label datasets have missing
values (`MultipleBinaryClassification` handles them).

## Molecular property — regression

| Class | Size | Property | Units |
|---|---|---|---|
| `ESOL` | 1,128 | Water solubility | log(mol/L) |
| `FreeSolv` | 642 | Hydration free energy | kcal/mol |
| `Lipophilicity` | 4,200 | LogD (octanol/water) | — |
| `SAMPL` | 643 | Solvation free energy | kcal/mol |

Metrics: MAE, RMSE, R².

## Quantum chemistry

| Class | Size | Targets | Notes |
|---|---|---|---|
| `QM7` | 7,165 | 1 | Atomization energy |
| `QM8` | 21,786 | 12 | Electronic spectra / excited states |
| `QM9` | 133,885 | 12 | Geometry, energy, electronic, thermodynamic |
| `PCQM4M` | ~3.8M | 1 | Large-scale HOMO-LUMO gap |

QM9 targets include dipole moment, polarizability, HOMO/LUMO, internal energy,
enthalpy, free energy, heat capacity. Pair with 3D-aware `SchNet`.

## Large molecule databases (generation / pretraining)

| Class | Size | Use |
|---|---|---|
| `ZINC250k` | 250,000 | Generative training |
| `ZINC2M` | 2,000,000 | Large-scale pretraining |
| `ChEMBL` | millions | Bioactive-molecule property/generation |

## Protein — function

| Class | Size | Task | Classes |
|---|---|---|---|
| `EnzymeCommission` | 17,562 | multi-class | EC hierarchy |
| `GeneOntology` | 46,796 | multi-label | 489 GO terms (BP/MF/CC) |
| `BetaLactamase` | 5,864 | regression | Enzyme activity |
| `Fluorescence` | 54,025 | regression | GFP fluorescence intensity |
| `Stability` | 53,614 | regression | Thermostability (ΔΔG) |

## Protein — localization and solubility

| Class | Size | Task |
|---|---|---|
| `Solubility` | 62,478 | binary solubility |
| `BinaryLocalization` | 22,168 | membrane vs. soluble |
| `SubcellularLocalization` | 8,943 | 10-class compartment |

## Protein — structure

| Class | Size | Task |
|---|---|---|
| `Fold` | 16,712 | fold recognition (1,195 classes) |
| `SecondaryStructure` | 8,678 | 3-/8-state per residue |
| `ProteinNet` | varies | residue-residue contacts |

## Protein interactions and binding

| Class | Size | Task |
|---|---|---|
| `HumanPPI` | 1,412 proteins / 6,584 interactions | PPI |
| `YeastPPI` | 2,018 proteins / 6,451 interactions | PPI |
| `PPIAffinity` | 2,156 pairs | binding affinity |
| `BindingDB` | ~1.5M | protein-ligand affinity |
| `PDBBind` | 20,000+ complexes | structure-based binding (Refined ~5,316; Core ~285) |

Large stores: `AlphaFoldDB` (200M+ predicted structures) and UniProt integration.

## Knowledge graphs

| Class | Entities | Relations | Triples | Domain |
|---|---|---|---|---|
| `FB15k` | 14,951 | 1,345 | 592,213 | Freebase |
| `FB15k237` | 14,541 | 237 | 310,116 | Filtered Freebase |
| `WN18` | 40,943 | 18 | 151,442 | WordNet |
| `WN18RR` | 40,943 | 11 | 93,003 | Filtered WordNet |
| `Hetionet` | 45,158 | 24 | 2,250,197 | Biomedical (29 databases) |

Hetionet entity types include genes (~20,945), compounds (~1,552), diseases,
anatomy, pathways, side effects, symptoms; relations include Compound-binds-Gene,
Gene-associates-Disease, Compound-treats-Disease, Compound-causes-Side-effect. It
is the workhorse for drug-repurposing link prediction.

## Citation networks

`Cora` (2,708 nodes / 7 classes), `CiteSeer` (3,327 / 6), `PubMed` (19,717 / 3) —
node-classification baselines for GNN development.

## Retrosynthesis

`USPTO50k` — 50,017 single-step patent reactions, atom-mapped, canonicalized
SMILES, product→reactants, roughly 40k/5k/5k train/valid/test. The standard (and in
practice only) built-in retrosynthesis benchmark.

## Loading and splitting

```python
from torchdrug import datasets, transforms

dataset = datasets.BBBP("~/molecule-datasets/")                 # auto-downloads
dataset = datasets.BBBP("~/data/", transform=transforms.VirtualNode())
protein_ds = datasets.EnzymeCommission("~/protein-datasets/")
kg = datasets.FB15k237("~/kg-datasets/")

# splits
train, valid, test = dataset.split()                # predefined, when available
train, valid, test = dataset.split([0.8, 0.1, 0.1]) # random ratios
```

For molecules prefer **scaffold splitting** (group by Bemis-Murcko scaffold) so
near-duplicate analogs do not straddle train/test and inflate scores. Datasets
expose `node_feature_dim`, `edge_feature_dim`, and `tasks` for wiring into a model
and task.

## Auto-extracted features

- Molecule nodes: atom type, formal charge, hybridization, aromaticity, hydrogen
  count, chirality.
- Molecule edges: bond type, stereochemistry, conjugation, ring membership.
- Protein nodes: residue type, physicochemical properties, sequence position,
  secondary structure, solvent accessibility.
- Protein edges: edge type (sequential/spatial/contact), distance, angles/dihedrals.

## Choosing by need

- Quick molecular-classification start → BBBP or HIV. Regression → ESOL / FreeSolv.
- Quantum properties → QM9 (with SchNet).
- Protein function → EnzymeCommission (clean classes) or GeneOntology (broad).
- Drug safety → Tox21 (standard) or ClinTox (clinical).
- Structure-based → PDBBind, ProteinNet.
- Knowledge graph → FB15k-237 (general benchmark), Hetionet (biomedical).
- Generation → ZINC250k (train), QM9 (with properties).
- Retrosynthesis → USPTO-50k.

Sizing: small (<5K) BACE/FreeSolv/ClinTox; medium (5K–100K) BBBP/HIV/Tox21/
EnzymeCommission/FB15k-237; large (>100K) QM9/MUV/GeneOntology/ZINC2M/BindingDB.

Report mean ± std over multiple seeds, keep a held-out test set, and watch for
leakage when using pretrained encoders.
