---
name: pytdc
version: 0.1.0
description: >-
  Load AI-ready drug-discovery datasets, standardized splits, evaluation metrics,
  and molecular oracles from Therapeutics Data Commons (PyTDC, the mims-harvard/TDC
  library). Covers single-instance prediction (ADME, toxicity, QM, HTS), multi-instance
  prediction (drug-target and drug-drug interaction, synergy, gene-disease), and
  generation (molecule generation, retrosynthesis), plus scaffold/cold/temporal
  splits, an Evaluator for ROC-AUC/RMSE/Spearman, oracle scoring for goal-directed
  design, and benchmark groups (ADMET). Use when building or benchmarking therapeutic
  ML models on pharmacological property prediction, binding, or molecule generation,
  or when you need reproducible splits for medicinal chemistry. Do
  NOT use for cheminformatics primitives like fingerprints, descriptors, or 3D
  conformers (use `rdkit` or `datamol`), for training ADMET/binding models end-to-end
  (that lives in `admet-prediction` / `binding-affinity`), or for fetching a single
  compound record (query PubChem/ChEMBL directly).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT (PyTDC / Therapeutics Data Commons, mims-harvard/TDC)"
---

# PyTDC (Therapeutics Data Commons)

## Overview

PyTDC (`pip install PyTDC`, imported as `tdc`) is a Python interface to Therapeutics
Data Commons: a curated collection of drug-discovery datasets packaged for machine
learning. Every dataset ships with a standard loader, meaningful train/valid/test
splits (scaffold, cold, temporal), and standardized evaluation metrics, so model
comparisons are reproducible rather than ad hoc.

TDC organizes tasks into three problem families, each a submodule:

- `tdc.single_pred` — predict a property of one entity (a molecule or protein).
- `tdc.multi_pred` — predict a property of an interaction between two entities.
- `tdc.generation` — generate new entities (molecules, reactants).

On top of datasets, TDC provides three cross-cutting tools: an `Evaluator` (metrics),
an `Oracle` (property scoring functions for generation), and `benchmark_group`
collections (leaderboard-style multi-dataset evaluation with a fixed seed protocol).

Use this skill to route to the right loader, split strategy, and evaluation tool.
Deep catalogs and long examples live in `references/`.

## When to Use This Skill

Use PyTDC when you need to:

- Load a curated therapeutic dataset (ADME, toxicity, DTI, DDI, synergy, QM, HTS)
  with a known train/valid/test split.
- Benchmark a model against a standardized protocol (e.g. the ADMET benchmark group,
  five seeds, fixed metric).
- Get a **scaffold** or **cold** split so test performance reflects generalization to
  new chemical matter or unseen drugs/targets, not memorization.
- Score generated molecules with an `Oracle` (QED, SA, DRD2, GSK3B, docking) for
  goal-directed or distribution-learning generation.
- Convert dataset labels between binding-affinity units, or convert SMILES to graph
  or fingerprint formats for a model.

## When NOT to Use This Skill

- **Cheminformatics primitives** — computing fingerprints, descriptors, 3D conformers,
  or substructure matches from scratch: use `rdkit` or `datamol`. TDC wraps these for
  format conversion but is not the primitive library.
- **End-to-end model training** for ADMET or binding: TDC supplies data + metrics; the
  modeling workflow lives in `admet-prediction`, `admet-reasoning`, or
  `binding-affinity`. Use `deepchem` if you want MoleculeNet-style datasets *and*
  built-in models in one package.
- **Goal-directed generation algorithms** themselves (the generator, the optimizer
  loop): TDC provides the oracle and the starting distribution; the search method
  belongs in `molecular-optimization`.
- **Fetching one compound or protein record**: query PubChem, ChEMBL, or UniProt
  directly rather than pulling a whole TDC dataset.

## Installation

```bash
uv pip install PyTDC          # imported as `tdc`
uv pip install PyTDC --upgrade
```

Core dependencies (numpy, pandas, scikit-learn, tqdm, seaborn, fuzzywuzzy) install
automatically. Some features pull extra packages on first use: `rdkit` for molecule
handling, `PyTorch Geometric`/`DGL` for graph conversion, docking backends for
docking oracles. Datasets download to the working directory (or the `path=` you pass)
on first load and are cached thereafter.

## Core Access Pattern

Every dataset follows the same shape:

```python
from tdc.single_pred import ADME
data  = ADME(name='Caco2_Wang')                 # downloads + caches on first call
split = data.get_split(method='scaffold', seed=1, frac=[0.7, 0.1, 0.2])
df    = data.get_data(format='df')              # full dataset as a DataFrame
```

- `get_data(format=...)` returns the whole set; `format` accepts `'df'`, `'dict'`,
  `'DeepPurpose'`, and graph formats where applicable.
- `get_split(...)` returns a dict `{'train', 'valid', 'test'}` of DataFrames.
- Dataset name matching is **fuzzy/case-insensitive** — `'Caco2_Wang'`, `'caco2_wang'`
  all resolve. A wrong name raises with a suggestion list.
- Single-prediction frames use columns `Drug_ID`, `Drug` (SMILES), `Y` (label).
  Interaction frames add `Target_ID`, `Target` (sequence), and a paired `Y`.

## Task Families

Pick a loader by problem family. The full dataset catalog (names, sizes, endpoints)
is in **`references/datasets.md`**.

**`tdc.single_pred`** — one entity in, one label out:
`ADME`, `Tox`, `HTS`, `QM`, `Yields`, `Epitope`, `Develop`, `CRISPROutcome`.

```python
from tdc.single_pred import Tox
data = Tox(name='hERG')          # cardiotoxicity; also AMES, DILI, ClinTox, LD50_Zhu
```

**`tdc.multi_pred`** — a pair of entities in, an interaction label out:
`DTI`, `DDI`, `PPI`, `GDA`, `DrugRes`, `DrugSyn`, `PeptideMHC`, `AntibodyAff`, `MTI`,
`Catalyst`, `TrialOutcome`.

```python
from tdc.multi_pred import DTI
data  = DTI(name='BindingDB_Kd')          # drug SMILES + target sequence -> affinity
split = data.get_split(method='cold_drug', seed=1)   # unseen drugs in the test set
```

**`tdc.generation`** — generate new entities: `MolGen`, `RetroSyn`, `PairMolGen`.

```python
from tdc.generation import MolGen
data = MolGen(name='ChEMBL_V29')          # ~1.9M drug-like SMILES to learn from
```

Score generated molecules with an oracle (see below and `references/oracles.md`).

## Splits, Evaluation, Oracles

These three tools are the reason to use TDC over raw CSVs. Depth for each is in
`references/utilities.md` (splits + metrics + data processing) and
`references/oracles.md` (oracles).

**Splits** — pass `method=` to `get_split`. Choosing the right one is the single most
important reproducibility decision:

- `scaffold` — Bemis–Murcko scaffold split; the realistic default for single-prediction
  chemistry. Test molecules have unseen scaffolds.
- `cold_drug` / `cold_target` / `cold_drug_target` — for `multi_pred`; hold out entire
  drugs and/or targets so the test set has none seen in training.
- `temporal` — time-based, for prospective-style evaluation.
- `random` — baseline only; over-optimistic for drug discovery.

**Evaluator** — standardized metrics; construct by name, call on `(y_true, y_pred)`:

```python
from tdc import Evaluator
roc = Evaluator(name='ROC-AUC')(y_true, y_pred_proba)   # classification
mae = Evaluator(name='MAE')(y_true, y_pred)             # regression
```

Common names: `ROC-AUC`, `PR-AUC`, `F1`, `Accuracy`, `RMSE`, `MAE`, `R2`, `Spearman`,
`Pearson`. Match the metric to the task type — full list in `references/utilities.md`.

**Oracle** — a scoring function for generation; construct by name, call on a SMILES
string or list:

```python
from tdc import Oracle
oracle = Oracle(name='DRD2')            # also QED, SA, GSK3B, JNK3, LogP, Docking, ...
score  = oracle('CC(C)Cc1ccc(cc1)C(C)C(O)=O')
scores = oracle(['SMILES1', 'SMILES2'])  # batch is faster than a loop
```

Rule-based oracles (QED, SA, LogP, Lipinski) are fast; ML oracles (DRD2, GSK3B) are
medium; docking oracles (Vina, ASKCOS) are slow and need extra backends. See
`references/oracles.md` for the full catalog and multi-objective patterns.

## Benchmark Groups

For leaderboard-comparable results, use a benchmark group instead of hand-rolling a
split. Groups enforce a fixed split and require reporting mean ± std over **five seeds**.

```python
from tdc.benchmark_group import admet_group
group     = admet_group(path='data/')
benchmark = group.get('Caco2_Wang')          # dict with 'train', 'valid', 'test'

predictions = {}
for seed in [1, 2, 3, 4, 5]:
    train, valid = benchmark['train'], benchmark['valid']
    # ... train your model on `train`/`valid`, predict on benchmark['test'] ...
    predictions[seed] = model.predict(benchmark['test'])

results = group.evaluate(predictions)        # -> {'caco2_wang': [mean, std]}
```

The ADMET group bundles 22 absorption/distribution/metabolism/excretion/toxicity
datasets. Full multi-seed evaluation walkthrough is in `references/utilities.md`.

## Boundaries and Failure Modes

- **First load downloads data.** Loading a large dataset (e.g. `BindingDB_IC50`, ~1M
  pairs) pulls hundreds of MB and can be slow/memory-heavy. Pass an explicit `path=`,
  check `references/datasets.md` for sizes, and prefer a smaller dataset when
  prototyping.
- **Never evaluate a `multi_pred` model on a `random` split** and claim generalization
  — drug/target leakage inflates scores. Use a cold split and assert no overlap.
- **Oracle scores are model predictions, not measurements.** Treat top candidates as
  hypotheses to validate experimentally; different oracles have different ranges and
  optimization directions (SA lower-is-better, DRD2 higher-is-better).
- **Docking/ASKCOS oracles need external software** and will fail without their backend
  installed — check `references/oracles.md` before relying on them.
- **Some utility signatures vary by TDC version.** For unit conversion, label
  binarization, and custom folds, confirm the exact call against the installed version
  (`references/utilities.md` flags the ones to verify).

## References

- **`references/datasets.md`** — full dataset catalog by task family, with names,
  sizes, and endpoints; how to enumerate datasets programmatically.
- **`references/oracles.md`** — every oracle (biochemical, physicochemical, composite,
  docking), speed/reliability notes, multi-objective and goal-directed workflows.
- **`references/utilities.md`** — split strategies, the full `Evaluator` metric list,
  molecule format conversion, filters, entity retrieval, and end-to-end pipelines.

Upstream: [tdcommons.ai](https://tdcommons.ai) · [tdc.readthedocs.io](https://tdc.readthedocs.io)
· [github.com/mims-harvard/TDC](https://github.com/mims-harvard/TDC) · NeurIPS 2021
Datasets & Benchmarks paper "Therapeutics Data Commons".
