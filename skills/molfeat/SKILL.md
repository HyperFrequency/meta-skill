---
name: molfeat
version: 0.1.0
description: >-
  Molfeat is a hub of 100+ molecular featurizers behind one scikit-learn-style
  API. Use it to turn SMILES / RDKit `Chem.Mol` objects into fixed-length
  vectors for molecular ML — fingerprints (ECFP, FCFP, MACCS, MAP4, atom-pair),
  physchem descriptors (RDKit 2D/3D, Mordred, E-State), pharmacophore/shape
  descriptors (CATS, Gobbi, USR), and pretrained deep embeddings (ChemBERTa,
  ChemGPT, MolT5, GIN, Graphormer) — with automatic parallelism, caching, and
  save/reload of the exact featurizer config. Reach for it to build the
  featurization front-end of QSAR/QSPR models, virtual screening, or similarity
  search, or to benchmark many representations under one interface. Do NOT use
  for low-level cheminformatics like standardization, scaffold splitting, or
  SMILES I/O (use `datamol` / `rdkit`), for the ML model itself (use
  `scikit-learn` / `pytorch-lightning`), for end-to-end molecular ML with
  built-in benchmarks and GNN training (use `deepchem`), or for explaining a
  trained model (use `shap`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "Apache-2.0 (molfeat, datamol-io)"
---

# Molfeat: Molecular Featurization Hub

## Overview

Molfeat is a Python library that unifies 100+ ways of turning a molecule into a
numeric vector behind a single, scikit-learn-compatible API. It spans the whole
spectrum of representations — hand-crafted fingerprints and physchem descriptors
on one end, pretrained transformer and graph-neural-network embeddings on the
other — so you can swap or combine featurizers without rewriting your pipeline.
It adds free parallelism, a caching layer for expensive pretrained models, and
serialization of the exact featurizer configuration for reproducible ML.

This skill is a **router**. It gives you the mental model, the quick-start path,
and a decision table for picking a featurizer, then delegates the full catalog,
the class-by-class API, and worked end-to-end workflows to `references/`.

The canonical pattern is always: define a **calculator** (what to compute for one
molecule), wrap it in a **transformer** (how to run it over a batch in parallel),
then feed the resulting array to a downstream model.

## When to Use This Skill

Trigger when the user wants to:
- Convert SMILES / `Chem.Mol` objects into ML-ready feature matrices
- Compute fingerprints (ECFP, FCFP, MACCS, MAP4, atom-pair, torsion, Avalon)
- Compute physchem descriptors (RDKit 2D/3D, Mordred, E-State) for interpretable models
- Get pharmacophore / 3D-shape descriptors (CATS, Gobbi, USR, ElectroShape)
- Extract pretrained deep embeddings (ChemBERTa, ChemGPT, MolT5, GIN, Graphormer)
- Featurize the input side of a QSAR/QSPR model, virtual screen, or similarity search
- Concatenate several featurizers into one representation (`FeatConcat`)
- Benchmark many molecular representations under one consistent interface
- Persist and reload the exact featurizer config for a reproducible pipeline

## When NOT to Use This Skill

- **Cheminformatics preprocessing** — standardization, salt stripping, SMILES/InChI
  conversion, scaffold extraction, dedup. Featurization assumes clean molecules;
  do that step with `datamol` (high level) or `rdkit` (low level) first.
- **The ML model itself** — molfeat produces `X`, not predictions. Train with
  `scikit-learn`, `pytorch-lightning`, XGBoost, etc.
- **End-to-end molecular ML with built-in benchmarks + GNN training loops** — if
  you want MoleculeNet loaders, scaffold splitters, and trainable graph nets in
  one package, use `deepchem`. Molfeat only emits features.
- **Explaining a trained model** — for SHAP/feature attribution use `shap`.
- **Proteins / nucleic acids / macromolecules** — molfeat targets small molecules.

## Install

```bash
uv pip install molfeat                 # core: fingerprints + descriptors
uv pip install "molfeat[all]"          # everything below
```

Pretrained featurizers need extras — install only what you use:

| Extra | Enables |
|-------|---------|
| `molfeat[transformer]` | ChemBERTa, ChemGPT, MolT5 (HuggingFace) |
| `molfeat[dgl]` | GIN variants, JT-VAE (DGL-LifeSci) |
| `molfeat[graphormer]` | Graphormer quantum-chemistry embeddings |
| `molfeat[fcd]` | Fréchet ChemNet Distance features |
| `molfeat[map4]` | MAP4 fingerprint |

`datamol` comes as a dependency and is the idiomatic way to load example data
(`dm.data.freesolv()`) and clean molecules before featurizing.

## The Three-Layer Model

Everything in molfeat is one of three things. Get this and the rest is naming.

1. **Calculator** (`molfeat.calc`) — a callable that featurizes **one** molecule.
   `calc("CCO")` returns a 1-D array. Use directly only for single molecules or
   custom loops.
2. **Transformer** (`molfeat.trans`) — wraps a calculator to featurize a **batch**
   in parallel and behaves like an sklearn transformer (`fit`/`transform`/
   `__call__`). This is what you use 90% of the time.
3. **Pretrained transformer** (`molfeat.trans.pretrained`) — a transformer for
   deep models (HuggingFace / DGL / Graphormer) that adds batched GPU inference
   and caching. Constructed with `kind="<model-name>"`, not by wrapping a calculator.

## Quick Start

```python
import datamol as dm
from molfeat.calc import FPCalculator
from molfeat.trans import MoleculeTransformer

smiles = dm.data.freesolv().sample(100).smiles.values

calc = FPCalculator("ecfp", radius=3, fpSize=2048)   # one-molecule featurizer
featurizer = MoleculeTransformer(calc, n_jobs=-1)    # parallel batch wrapper

X = featurizer(smiles)          # -> np.ndarray, shape (100, 2048)
featurizer.to_state_yaml_file("ecfp.yml")            # freeze exact config
# later / elsewhere:
featurizer = MoleculeTransformer.from_state_yaml_file("ecfp.yml")
```

Pretrained embeddings use the dedicated classes (note `kind=`, not a wrapped calc):

```python
from molfeat.trans.pretrained import PretrainedHFTransformer, PretrainedDGLTransformer

chemberta = PretrainedHFTransformer(kind="ChemBERTa-77M-MLM", notation="smiles")
gin       = PretrainedDGLTransformer(kind="gin_supervised_masking")
emb = chemberta(smiles)         # -> (100, 768)
```

See `references/workflows.md` for QSAR, virtual screening, similarity search,
and sklearn/PyTorch integration end-to-end.

## Choosing a Featurizer

| Goal | Start with | Notes |
|------|-----------|-------|
| General ML baseline (RF/SVM/XGB) | `ecfp` | radius 3, 2048 bits; the go-to workhorse |
| Fast scaffold-level similarity | `maccs` | 167 fixed keys, very fast |
| Interpretable model | `desc2D` (RDKit) or `mordred` | named physchem columns via `.columns` |
| Large-scale screening / search | `map4` or `ecfp` | MAP4 is compact (1024) and fast |
| Pharmacophore reasoning | `fcfp`, `cats2D`, `gobbi2D` | functional-group / pharmacophore based |
| 3D shape similarity | `usr`, `usrcat`, `electroshape` | need conformers first |
| Transfer learning / SOTA embeddings | `ChemBERTa-77M-MLM`, `ChemGPT-*` | slow first run, then cached |
| Graph-based embeddings | `gin_supervised_masking`/`-infomax`/`-edgepred` | needs `molfeat[dgl]` |
| Quantum-property style embedding | `Graphormer-pcqm4mv2` | needs `molfeat[graphormer]` |

Combine representations with `FeatConcat` (e.g. `maccs` 167 + `ecfp` 2048 →
2215-dim). Full catalog with dimensions, speed tiers, and dependencies is in
`references/featurizer-catalog.md`.

## Discovering Featurizers Programmatically

```python
from molfeat.store.modelstore import ModelStore

store = ModelStore()
store.available_models                       # every registered featurizer
card = store.search(name="ChemBERTa-77M-MLM")[0]
card.usage()                                 # prints a runnable snippet
transformer = store.load("ChemBERTa-77M-MLM")  # load by name
```

## Failure Modes to Anticipate

- **Invalid SMILES kill a whole batch by default.** Pass `ignore_errors=True`
  (and `verbose=True`) to `MoleculeTransformer`; failed molecules come back as
  `None` — filter them and keep a mask so `X` and `y` stay aligned.
- **Pretrained models are slow and heavy on first call.** They download weights
  and run on CPU unless a GPU is present; rely on molfeat's caching and persist
  embeddings for large libraries (see `references/workflows.md`).
- **3D descriptors need conformers.** `desc3D`, `cats3D`, `usr`, `electroshape`
  require a molecule with a generated conformer, not a bare SMILES string.
- **Reproducibility.** Always `to_state_yaml_file(...)` the fitted transformer and
  record `molfeat.__version__`; a bare method name does not pin `radius`/`fpSize`.
- **Scale.** Featurize >100K molecules in chunks and `np.vstack` to bound memory.

## References

- `references/api-reference.md` — class-by-class API for `molfeat.calc`,
  `molfeat.trans`, `molfeat.trans.pretrained`, and `molfeat.store`, with
  parameters, state-management methods, and dtype control. Load when writing a
  specific calculator/transformer or tuning parameters.
- `references/featurizer-catalog.md` — the full 100+ featurizer catalog by
  category (language models, GNNs, descriptors, fingerprints, pharmacophore,
  shape, scaffold, graph-input features) with dimensions, speed, and required
  extras. Load when selecting or comparing featurizers.
- `references/workflows.md` — copy-paste workflows: QSAR modeling, virtual
  screening, similarity search, sklearn pipelines / grid search, PyTorch
  datasets, custom preprocessing, chunked featurization, embedding caching, and
  troubleshooting. Load when implementing an end-to-end task.

## External Documentation

- Docs: https://molfeat-docs.datamol.io/
- Source: https://github.com/datamol-io/molfeat
