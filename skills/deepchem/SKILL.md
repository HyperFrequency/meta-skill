---
name: deepchem
version: 0.1.0
description: >-
  DeepChem applies machine learning to molecules, materials, and biological
  sequences from one Python API. Use it to featurize molecules (circular/Morgan
  fingerprints, RDKit/Mordred descriptors, graph representations), load
  MoleculeNet benchmarks (Tox21, BBBP, Delaney/ESOL, FreeSolv, QM9), split
  without structural leakage (ScaffoldSplitter), and train property / ADMET /
  toxicity / solubility predictors spanning scikit-learn wrappers, multitask
  nets, graph neural networks (GCN, GAT, AttentiveFP, DMPNN), and fine-tuned
  chemical language models (ChemBERTa, MoLFormer). Reach for it when you want a
  single interface across many molecular representations, ready-made benchmarks,
  and a fast path from baseline to GNN. Do NOT use for pure
  cheminformatics with no ML (use `rdkit`), explaining an already-trained model
  (use `shap`), plain tabular ML with hand-built features (use `scikit-learn`),
  or when you need one bespoke graph architecture and full control in raw
  PyTorch (write it directly with `pytorch-lightning`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "DeepChem (MIT)"
---

# DeepChem: Molecular Machine Learning

## Overview

DeepChem is a Python library for machine learning on chemistry, materials, and
biology. It standardizes the messy front end of molecular ML — turning SMILES,
SDF, and sequence data into ML-ready tensors — behind one `Dataset` object, then
gives you a wide model zoo (scikit-learn wrappers, multitask MLPs, graph neural
networks, pretrained chemical transformers) that all share the same
`fit` / `predict` / `evaluate` interface. It also ships **MoleculeNet**, a
collection of curated benchmark datasets with standard splits.

This SKILL is a **router**. It gives the mental model, the quick-start path, and
the boundaries, then delegates the full featurizer/model catalog and end-to-end
recipes to `references/`. The whole library reduces to a five-stage pipeline:
**load → featurize → split → train → evaluate/predict**. Every task is a choice
of which class to plug into each stage.

## When to Use This Skill

Reach for DeepChem when you need to:

- Predict a **molecular property** — solubility, lipophilicity, toxicity,
  binding, or an ADMET endpoint — from SMILES or SDF input.
- Get a **quick, credible baseline** across several molecular representations
  without hand-wiring each featurizer to each model.
- Evaluate against **MoleculeNet benchmarks** (Tox21, BBBP, HIV, BACE, ClinTox,
  Delaney/ESOL, FreeSolv, Lipophilicity, QM7/8/9) with standard scaffold splits.
- Train **graph neural networks** on molecules (GCN, GAT, AttentiveFP, DMPNN)
  without building the graph-featurization plumbing yourself.
- **Fine-tune a pretrained chemical language model** (ChemBERTa, MoLFormer) on a
  small labeled set.
- Split molecular data **without leakage** via scaffold/Butina splitting so
  near-duplicate structures do not straddle train and test.

## When NOT to Use This Skill

- **Pure cheminformatics with no ML** — computing descriptors, standardizing,
  substructure search, or drawing molecules — use `rdkit` directly.
- **Explaining an already-trained model** (feature attributions) — use `shap`.
- **Plain tabular ML** on features you already have — use `scikit-learn`
  (DeepChem only adds overhead if you are not using its featurizers or datasets).
- **One bespoke graph architecture** with full training-loop control — write it
  in raw PyTorch / `pytorch-lightning`; DeepChem's wrappers trade flexibility for
  convenience.
- **Dimensionality reduction / clustering** of learned embeddings — pair the
  model's outputs with `umap-learn` and `scikit-learn`.

## Installation

```bash
uv pip install deepchem            # core (scikit-learn models, featurizers, MoleculeNet)
uv pip install deepchem[torch]     # PyTorch models: GCN, GAT, AttentiveFP, DMPNN, transformers
uv pip install deepchem[all]       # everything, including materials + generative extras
```

Graph models depend on PyTorch (and, for some, DGL/PyG); `dc.feat.RDKitDescriptors`
and fingerprints require RDKit, which `deepchem` pulls in. Import as
`import deepchem as dc`.

## Quick start

```python
import deepchem as dc

# Load a benchmark with fingerprint features and a leakage-safe split
tasks, datasets, transformers = dc.molnet.load_delaney(
    featurizer="ECFP", splitter="scaffold"
)
train, valid, test = datasets

# A strong, fast baseline: multitask regressor over the fingerprint
model = dc.models.MultitaskRegressor(
    n_tasks=len(tasks), n_features=1024, layer_sizes=[1000, 500], dropouts=0.25
)
model.fit(train, nb_epoch=50)

metric = dc.metrics.Metric(dc.metrics.r2_score)
print("test R^2:", model.evaluate(test, [metric], transformers))
```

For your own CSV, replace the first block with a loader:

```python
featurizer = dc.feat.CircularFingerprint(radius=2, size=2048)
loader = dc.data.CSVLoader(tasks=["activity"], feature_field="smiles", featurizer=featurizer)
dataset = loader.create_dataset("molecules.csv")
train, valid, test = dc.splits.ScaffoldSplitter().train_valid_test_split(dataset)
```

## Choosing a featurizer

Match the representation to the model family — this is the decision that most
affects results:

- **Traditional ML (RF, XGBoost, SVM):** `CircularFingerprint` (ECFP/Morgan) for
  a fast baseline; `RDKitDescriptors` (~200 physicochemical descriptors) when you
  want interpretability; `MordredDescriptors` for maximum coverage.
- **Graph neural networks:** `MolGraphConvFeaturizer` (GCN/GAT), `DMPNNFeaturizer`
  (message passing), `WeaveFeaturizer` (Weave nets).
- **Sequence / transformer models:** raw SMILES (`DummyFeaturizer`, model handles
  tokenization) or `SmilesToSeq`.
- **3D / quantum:** `CoulombMatrix`.

The featurizer and model must agree (a fingerprint featurizer cannot feed a GNN).
MoleculeNet's `featurizer=` string is a shortcut: `"ECFP"`, `"GraphConv"`,
`"Weave"`, `"Raw"`. See `references/api-reference.md` for the full catalog,
parameters, and a selection table.

## Choosing a model

| Dataset size | Good first choice | Featurizer |
|---|---|---|
| < 1K | `SklearnModel(RandomForestRegressor(...))` | `CircularFingerprint` / `RDKitDescriptors` |
| 1K–100K | `MultitaskRegressor` / `MultitaskClassifier` or `GBDTModel` | `CircularFingerprint` |
| > ~10K | `GCNModel`, `AttentiveFPModel`, `DMPNNModel` | `MolGraphConvFeaturizer` |
| Small + novel scaffolds | fine-tune ChemBERTa / MoLFormer | model-specific |

Start simple and only climb this ladder when the simpler model plateaus — GNNs
typically need >10K samples to beat a good fingerprint baseline. Full model
catalog (materials CGCNN/MEGNet, generative MolGAN, physics-informed) is in
`references/api-reference.md`.

## Data splitting — avoid structural leakage

**Critical for drug discovery.** A random split lets near-identical analogs sit
in both train and test, inflating scores. Use scaffold splitting so whole
Bemis–Murcko scaffolds go entirely to one side:

```python
train, valid, test = dc.splits.ScaffoldSplitter().train_valid_test_split(dataset)
```

Alternatives: `ButinaSplitter` (fingerprint clustering), `MaxMinSplitter`
(diversity), `RandomStratifiedSplitter` (imbalanced labels). Reserve
`RandomSplitter` for non-molecular data.

## Transfer learning

For small or novel datasets, fine-tuning a pretrained chemical language model
often beats training from scratch. DeepChem exposes these through wrappers such
as `HuggingFaceModel` and dedicated classes (`Chemberta`, `MoLFormer`). Use a low
learning rate (~2e-5) and few epochs. The exact constructor takes a model object
plus tokenizer (not merely a name string) and evolves between releases — confirm
the current signature in `references/workflows.md` and the DeepChem docs before
relying on it.

## Evaluation

Wrap any metric in `dc.metrics.Metric` and pass a list to `model.evaluate`,
supplying the `transformers` so predictions are inverse-transformed to real
units:

```python
metrics = [dc.metrics.Metric(dc.metrics.roc_auc_score, name="ROC-AUC")]
scores = model.evaluate(test, metrics, transformers)
```

Common choices: `roc_auc_score`, `prc_auc_score`, `balanced_accuracy_score`,
`f1_score` (classification); `r2_score`, `mean_absolute_error`,
`root_mean_squared_error` (regression). See `references/api-reference.md`.

## Failure modes and boundaries

- **Random split on molecules → inflated metrics.** Default to `ScaffoldSplitter`
  for anything drug-like.
- **GNN underperforming fingerprints.** Usually too little data (<10K) or too few
  epochs — try `AttentiveFPModel`/`DMPNNModel`, more epochs, or a pretrained
  model before blaming the architecture.
- **Overfitting small datasets.** Prefer Random Forest or transfer learning;
  raise dropout; do not reach for a large GNN.
- **Out-of-memory on large sets.** Use `DiskDataset.from_numpy(...)` instead of
  `NumpyDataset`, and shrink `batch_size`.
- **Forgetting to inverse-transform.** Pass `transformers` to `evaluate` /
  `predict` or your regression errors will be in normalized space.
- **Import errors.** Graph and transformer models need `deepchem[torch]`;
  materials/generative extras need `deepchem[all]`.

## References

- `references/api-reference.md` — full catalog: data loaders, dataset classes,
  splitters, transformers, the complete featurizer list with a selection table,
  the model zoo by category (sklearn, GNN, materials, generative, physics-informed,
  vision, transformers), the MoleculeNet dataset index, and available metrics.
- `references/workflows.md` — end-to-end recipes: custom-CSV property prediction,
  benchmark evaluation, hyperparameter search with `GridHyperparamOpt`, transfer
  learning, molecular generation with MolGAN, materials properties, protein
  sequences, and wrapping your own scikit-learn / PyTorch model.

## Sibling skills

- `rdkit` — the cheminformatics layer underneath DeepChem's featurizers; use
  directly for descriptors, standardization, and drawing without ML.
- `scikit-learn` — the estimators DeepChem's `SklearnModel` wraps; use standalone
  for plain tabular ML.
- `shap` — explain a trained property predictor's feature attributions.
- `transformers` — the Hugging Face backbone behind ChemBERTa / MoLFormer.
- `umap-learn` — reduce and visualize learned molecular embeddings.
- `pytorch-lightning` — build a fully custom molecular architecture when
  DeepChem's wrappers are too rigid.
