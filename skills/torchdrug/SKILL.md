---
name: torchdrug
version: 0.1.0
description: >-
  PyTorch toolbox for graph machine learning on molecules, proteins, and
  biomedical knowledge graphs. Use it to build and train GNNs (GIN, GAT, RGCN,
  SchNet, GearNet), predict molecular or protein properties, complete knowledge
  graphs (TransE, RotatE, ComplEx), generate molecules (GCPN, GraphAF), and plan
  retrosynthesis (reaction-center identification + synthon completion) over 40+
  built-in datasets, all wired through one load to model to task to Engine
  pipeline. Reach for it when you need low-level control over graph
  architectures and task definitions for drug discovery or protein modeling in
  native PyTorch. Do NOT use for pure cheminformatics with no ML (use `rdkit`),
  a fast pretrained/featurizer-rich baseline across many representations (use
  `deepchem`), standardized benchmark datasets and leaderboards (use `pytdc`),
  protein language-model embeddings alone (use `esm`), or docking a ligand into
  a structure (use `diffdock`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "TorchDrug (Apache-2.0)"
---

# TorchDrug: Graph ML for Drug Discovery and Proteins

## Overview

TorchDrug is a PyTorch library for machine learning on graph-structured
scientific data — small molecules, proteins, and biomedical knowledge graphs. It
separates a problem into three composable pieces: a **data** structure
(`Graph` / `Molecule` / `Protein`), a **representation model** (a GNN or
embedding model that turns the graph into vectors), and a **task** (a learning
objective plus its metrics). You wire these together and hand them to a training
engine.

This SKILL is a **router**. It gives the mental model, an idiomatic quick start,
and the boundaries, then delegates the full model/dataset catalogs and per-task
recipes to `references/`. The whole library reduces to one pipeline:
**load a dataset → build a model → wrap it in a task → train with `core.Engine`
→ evaluate**. Every capability below is a different choice at the model and task
stages.

## When to Use This Skill

Reach for TorchDrug when you need to:

- **Build a custom GNN** for molecules or proteins and control the architecture,
  message passing, readout, and loss directly in PyTorch.
- **Predict molecular properties** (solubility, toxicity, activity, quantum
  properties) from SMILES or graphs.
- **Model proteins** from sequence (ESM, ProteinBERT, ProteinLSTM) or 3D
  structure (GearNet, SchNet) for function, stability, or localization.
- **Complete a knowledge graph** — link prediction / drug repurposing over
  Hetionet or FB15k-237 with TransE, RotatE, ComplEx, and friends.
- **Generate molecules** de novo, optionally property-optimized, with
  autoregressive, flow (GraphAF), or RL-policy (GCPN) methods.
- **Plan retrosynthesis** by decomposing it into reaction-center identification
  then synthon completion.

## When NOT to Use This Skill

- **Pure cheminformatics with no ML** — descriptors, standardization,
  substructure search, drawing — use `rdkit` (or `datamol`).
- **A fast, pretrained-heavy baseline** across many featurizers/models with
  MoleculeNet loaders and `fit`/`predict` convenience — use `deepchem`; it is
  higher-level and more actively maintained.
- **Standardized benchmark datasets, splits, and leaderboards** — use `pytdc`
  (Therapeutics Data Commons).
- **Protein embeddings from a language model alone** — use `esm` directly.
- **Docking a ligand into a receptor** — use `diffdock`.
- **A one-off graph model with full training-loop control** and no need for
  TorchDrug's task/dataset scaffolding — write it in raw PyTorch /
  `pytorch-lightning`.

## Installation

```bash
uv pip install torchdrug
# or, to avoid torch-scatter/torch-cluster wheel pain:
# conda install -c milagraph -c conda-forge torchdrug
```

TorchDrug pulls in RDKit and depends on `torch-scatter` / `torch-cluster`, whose
wheels must match your installed PyTorch and CUDA versions — this is the most
common install failure. Pin `torch` first, then install the scatter/cluster
extensions for that exact build. TorchDrug is **not actively maintained** (latest
release 0.2.x); if you want a modern, maintained stack, prefer `deepchem` or
raw PyTorch Geometric. See `references/core-concepts.md` for details.

## Quick start — the load → model → task → engine pipeline

```python
import torch
from torchdrug import datasets, models, tasks, core

# 1. Load a benchmark; split() returns train/valid/test subsets
dataset = datasets.BBBP("~/molecule-datasets/")
train_set, valid_set, test_set = dataset.split()

# 2. Build a representation model (GIN is the strong default for molecules)
model = models.GIN(
    input_dim=dataset.node_feature_dim,
    hidden_dims=[256, 256, 256, 256],
    edge_input_dim=dataset.edge_feature_dim,
    batch_norm=True,
    readout="mean",
)

# 3. Wrap it in a task (defines loss + metrics)
task = tasks.PropertyPrediction(
    model,
    task=dataset.tasks,
    criterion="bce",
    metric=("auprc", "auroc"),
)

# 4. Train and evaluate with the built-in engine
optimizer = torch.optim.Adam(task.parameters(), lr=1e-3)
solver = core.Engine(task, train_set, valid_set, test_set, optimizer,
                     gpus=[0], batch_size=32)
solver.train(num_epoch=100)
solver.evaluate("valid")
```

`core.Engine` is the idiomatic training path (handles batching, device placement,
logging). You can also drive a plain PyTorch loop by calling `task(batch)` for the
loss and `task.predict` / `task.target` / `task.evaluate` for evaluation — see
`references/core-concepts.md`.

Load your own molecules with `data.Molecule.from_smiles(...)` and construct a
dataset, or a protein with `data.Protein.from_pdb(...)` /
`data.Protein.from_sequence(...)`.

## Choosing a model

The single most important decision. Match the model to the data and task:

| Data / task | First choice | Notes |
|---|---|---|
| Molecular property (2D graph) | `models.GIN` | Most expressive GNN; strong default |
| Molecules, interpretable | `models.GAT` | Attention over neighbors |
| 3D / quantum (QM9) | `models.SchNet` | Distance-aware, rotation invariant |
| Multi-relational / reactions | `models.RGCN` | Per-bond-type weights |
| Protein, sequence only | `models.ESM` | Pretrained; fine-tune with low LR |
| Protein, 3D structure | `models.GearNet` | Geometry-aware, multi-edge |
| Knowledge graph | `models.RotatE` / `models.ComplEx` | Link prediction |
| Molecule generation | GraphAF (flow) / GCPN (RL) | Property optimization |

Start with the simplest model that fits your data size and only climb to deeper
or pretrained models when it plateaus. Full architecture catalog, parameters, and
a size/budget-based selection guide are in `references/models.md`.

## Task recipes

Each scientific task maps to a TorchDrug `tasks.*` class. Full workflows,
parameters, dataset choices, evaluation protocols, and failure modes live in the
references:

- **Molecular property prediction** (`tasks.PropertyPrediction`,
  `tasks.MultipleBinaryClassification`) and **molecule generation**
  (`tasks.AutoregressiveGeneration`, `tasks.GCPNGeneration`) and
  **retrosynthesis** (`tasks.CenterIdentification`, `tasks.SynthonCompletion`,
  `tasks.Retrosynthesis`) → `references/molecular-tasks.md`.
- **Protein modeling** (property, node-level, interaction, contact prediction;
  sequence vs. structure models; pretraining) and **knowledge-graph reasoning**
  (`tasks.KnowledgeGraphCompletion`, negative sampling, ranking metrics) →
  `references/protein-and-kg.md`.
- **Dataset catalog** — 40+ datasets across molecules, proteins, knowledge
  graphs, and reactions, with sizes, tasks, and splitting strategies →
  `references/datasets.md`.

## Failure modes and boundaries

- **`torch-scatter` / `torch-cluster` install errors.** Match their wheels to
  your exact `torch` + CUDA build, or use the conda channel above.
- **Dimension mismatch.** `model.input_dim` must equal `dataset.node_feature_dim`
  (and `edge_input_dim` = `dataset.edge_feature_dim` if the model uses edges).
- **Random split inflates molecular metrics.** Use scaffold splitting so similar
  structures do not straddle train/test — see `references/datasets.md`.
- **Protein model won't learn.** For sequence tasks, start from pretrained ESM
  with a small learning rate; for structure tasks, verify edge construction.
- **Out of memory on large graphs.** Reduce `batch_size`, accumulate gradients,
  or truncate long proteins.
- **Generated molecules invalid.** Add validity constraints and post-filter with
  RDKit — see `references/molecular-tasks.md`.
- **KG training slow.** Reduce `num_negative`, use DistMult for speed, and always
  report filtered ranking metrics.

## References

- `references/core-concepts.md` — architecture philosophy, `Graph`/`Molecule`/
  `Protein`/`PackedGraph` data structures, the model and task interfaces, the
  `core.Engine` and manual training loops, losses/metrics, transforms,
  self-supervised pretraining, custom layers, install notes, and pitfalls.
- `references/models.md` — full model catalog (GNNs, protein models, KG embedding
  models, generative, pretraining) with parameters and a selection guide.
- `references/datasets.md` — the complete dataset index with sizes/tasks,
  loading, and splitting strategies.
- `references/molecular-tasks.md` — property prediction, generation, and
  retrosynthesis workflows.
- `references/protein-and-kg.md` — protein modeling and knowledge-graph reasoning
  workflows.

## Sibling skills

- `rdkit` / `datamol` — cheminformatics under the hood; use directly for
  descriptors, standardization, and drawing.
- `deepchem` — higher-level molecular ML with pretrained models and MoleculeNet;
  reach for it first for a quick baseline.
- `pytdc` — benchmark datasets, splits, and leaderboards.
- `esm` — standalone protein language-model embeddings.
- `diffdock` — molecular docking.
- `pytorch-lightning` — build a fully custom graph model when TorchDrug's task
  scaffolding is too rigid.
- `shap` — explain a trained property predictor's attributions.
