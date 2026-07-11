# Molfeat Featurizer Catalog

The 100+ featurizers in molfeat, organized by category, with dimensions, speed,
and required extras. Grep this file for a family, e.g.:

```bash
grep -i "chembert" references/featurizer-catalog.md
grep -i "pharmacophore" references/featurizer-catalog.md
```

---

## Transformer-based language models

Pretrained on SMILES/SELFIES; loaded via `PretrainedHFTransformer(kind=...)`.
Needs `molfeat[transformer]`.

- **ChemBERTa-77M-MLM** — RoBERTa masked LM, 77M PubChem compounds; 768-dim
- **ChemBERTa-77M-MTR** — multitask-regression variant on PubChem
- **Roberta-Zinc480M-102M** — RoBERTa MLM trained on ~480M ZINC SMILES
- **GPT2-Zinc480M-87M** — GPT-2 autoregressive LM on ~480M ZINC SMILES
- **ChemGPT-1.2B / -19M / -4.7M** — autoregressive LMs on PubChem10M (use `notation="selfies"`)
- **MolT5** — self-supervised molecule↔text captioning/generation model

## Graph neural networks (GNNs)

Loaded via `PretrainedDGLTransformer(kind=...)` (needs `molfeat[dgl]`) or the
Graphormer transformer (needs `molfeat[graphormer]`).

GIN variants, all pretrained on ChEMBL with different self-supervised objectives:

- **gin_supervised_masking** — node masking
- **gin_supervised_infomax** — graph-level mutual-information maximization
- **gin_supervised_edgepred** — edge prediction
- **gin_supervised_contextpred** — context prediction

Other graph models:

- **jtvae_zinc_no_kl** — junction-tree VAE (ZINC), generation-oriented
- **Graphormer-pcqm4mv2** — graph transformer on PCQM4Mv2 quantum-chemistry data (HOMO-LUMO gap)

## Molecular descriptors

Interpretable, named physico-chemical properties (`molfeat.calc`).

- **desc2D / rdkit2D** — 200+ RDKit 2D descriptors (MW, logP, TPSA, HBD/HBA,
  rotatable bonds, ring counts, complexity)
- **desc3D / rdkit3D** — RDKit 3D descriptors (inertial moments, PMI ratios,
  asphericity, eccentricity, radius of gyration) — needs a conformer
- **mordred** — 1800+ descriptors (constitutional, topological, connectivity,
  information content, 2D/3D autocorrelations, WHIM, GETAWAY) — needs `mordred`
- **estate** — electrotopological-state (E-State) indices

## Molecular fingerprints

Fixed-length binary/count vectors via `FPCalculator("<name>")`.

Circular (ECFP family):

- **ecfp** — extended-connectivity, default radius 2 (ECFP4) / 2048 bits; general-purpose workhorse
- **ecfp-count** — count version
- **fcfp / fcfp-count** — functional-class variant (pharmacophore-flavored)

Path/pattern:

- **rdkit** — topological (linear-path) fingerprints
- **pattern** — automated pattern keys
- **layered** — multi-layer substructure fingerprint

Key-based:

- **maccs** — 167 predefined structural keys; fast, good for scaffold hopping
- **avalon** — Avalon fingerprints; more features than MACCS

Atom-pair / torsion:

- **atompair / atompair-count** — atom pairs + through-bond distance
- **topological / topological-count** — topological torsions (4-atom sequences)

MinHashed / specialized:

- **map4** — MinHashed atom-pair up to 4 bonds; 1024-dim, fast, large-scale friendly (needs `molfeat[map4]`)
- **secfp** — SMILES extended-connectivity fingerprint (operates on SMILES)
- **erg** — extended reduced graph (pharmacophoric points, reduced complexity)

## Pharmacophore descriptors

- **cats2D / cats3D** — CATS pharmacophore-pair distributions (2D topological or
  3D euclidean distances); vector length scales with `max_dist` / `bins` — read
  it off `len(calc)`
- **gobbi2D** — Gobbi 2D pharmacophore fingerprints (hydrophobic, aromatic, HBA,
  HBD, +/- ionizable, etc.); good for virtual screening
- **pmapper2D / pmapper3D** — Pmapper pharmacophore signatures

## Shape descriptors (require conformers)

- **usr** — ultrafast shape recognition; 12 dims, extremely fast
- **usrcat** — USR + pharmacophoric constraints; 60 dims
- **electroshape** — shape + chirality + electrostatics; useful for docking-style similarity

## Scaffold-based

- **scaffoldkeys** — 40+ scaffold-based properties (bioisosteric core representation)

## Graph-input features (for building GNN inputs)

- **atom-onehot / atom-default** — atom-level features (atomic number, degree,
  formal charge, hybridization, aromaticity, H count)
- **bond-onehot / bond-default** — bond-level features (type, conjugation, ring
  membership, stereochemistry)

## Integrated collections

Molfeat federates models from several sources: HuggingFace (ChemBERTa, ChemGPT,
MolT5), DGL-LifeSci (GIN, AttentiveFP, MPNN), Microsoft Graphormer, and FCD.

---

## Selection cheat-sheet

- **Traditional ML** → start `ecfp` or `maccs`; `desc2D` for interpretability;
  `FeatConcat` to combine.
- **Deep learning** → `ChemBERTa`/`ChemGPT` (sequence) or `gin_supervised_*`
  (graph); `Graphormer` for quantum-style properties.
- **Similarity search** → `ecfp` (general), `maccs` (fast), `map4` (large-scale),
  `usr`/`usrcat` (3D shape).
- **Pharmacophore** → `fcfp`, `cats2D`/`cats3D`, `gobbi2D`.
- **Interpretability** → `desc2D`, `mordred`, `maccs`, `scaffoldkeys`.

## Speed tiers

- **Fastest** — `maccs`, `ecfp`, `rdkit`, `usr`
- **Medium** — `desc2D`, `cats2D`, most fingerprints
- **Slower** — `mordred` (1800+), `desc3D` and other 3D descriptors (conformer generation)
- **Slowest (first run)** — pretrained models (ChemBERTa, ChemGPT, GIN); cached afterward

## Dimensionality

- **< 200** — `maccs` (167), `usr` (12), `usrcat` (60)
- **200–2000** — `desc2D` (~200), `ecfp` (2048 default), `map4` (1024 default)
- **> 2000** — `mordred` (1800+), concatenated fingerprints
- **Variable** — transformer embeddings (typically 768–1024), GNN embeddings

## Extras required

| Featurizers | Install |
|-------------|---------|
| GIN, JT-VAE | `molfeat[dgl]` |
| Graphormer | `molfeat[graphormer]` |
| ChemBERTa, ChemGPT, MolT5 | `molfeat[transformer]` |
| FCD | `molfeat[fcd]` |
| MAP4 | `molfeat[map4]` |
| Everything | `molfeat[all]` |

Discover the live list at runtime with `ModelStore().available_models` (see
`api-reference.md`).
