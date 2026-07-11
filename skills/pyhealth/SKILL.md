---
name: pyhealth
version: 0.1.0
description: >-
  Build, train, and evaluate clinical prediction models on electronic health
  records, physiological signals, medical images, and clinical text with
  PyHealth's unified dataset -> task -> model -> train -> calibrate pipeline. Use
  when working with MIMIC-III/IV, eICU, OMOP, or sleep/EEG datasets; standard
  clinical tasks (mortality, 30-day readmission, length-of-stay, drug
  recommendation, sleep staging, ICD coding); healthcare-specific models (RETAIN,
  SafeDrug, GAMENet, StageNet, SparcNet); medical-code translation across
  ICD/NDC/ATC/CCS; or clinical-grade calibration, conformal prediction sets, and
  fairness checks. Not for general non-clinical tabular ML (use `scikit-learn`),
  hand-rolled deep-learning training loops (use `pytorch-lightning`),
  model-agnostic explanations in isolation (use `shap`), or fine-tuning clinical
  language models outside PyHealth (use `transformers`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: MIT
---

# PyHealth: Clinical Prediction Modeling

## Overview

PyHealth (`sunlabuiuc/PyHealth`, MIT) is a PyTorch toolkit for healthcare AI. It
standardizes the whole clinical-ML loop behind one contract: load a raw
healthcare dataset, attach a prediction **task** that emits per-sample
input/output pairs, hand those to a **model** that reads named `feature_keys`,
then **train** and **calibrate** with a single `Trainer`. The same five stages
work across EHR event streams, biosignals (EEG/ECG), medical images, and
clinical text, so switching from mortality prediction to sleep staging changes a
few lines, not the architecture of your code.

Use this skill to route a clinical-ML task through PyHealth correctly on the
first try, and to sidestep the two mistakes that quietly ruin healthcare models:
patient-level data leakage and uncalibrated probabilities presented as risk.

## When to Use This Skill

Reach for PyHealth when the request involves:

- **Named clinical datasets** — MIMIC-III, MIMIC-IV, eICU, OMOP CDM, EHRShot, or
  signal sets (SleepEDF, SHHS, ISRUC, TUAB/TUEV/TUSZ), medical imaging, or notes.
- **Standard clinical tasks** — in-hospital / next-visit mortality, 30-day
  readmission, length-of-stay, drug recommendation, sleep staging, EEG
  abnormality/seizure detection, or ICD coding from text.
- **Healthcare-specific models** — interpretable (RETAIN, AdaCare, ConCare),
  DDI-aware medication recommenders (SafeDrug, GAMENet, MICRON, MoleRec),
  stage-aware (StageNet), or signal nets (SparcNet, ContraWR).
- **Medical-code work** — translating or grouping across ICD-9/10-CM, ICD-PROC,
  NDC, RxNorm, ATC, and CCS, or climbing a coding hierarchy.
- **Clinical-grade evaluation** — calibration, conformal prediction sets with
  coverage guarantees, uncertainty, and fairness across demographic subgroups.

## When NOT to Use This Skill

- **General non-clinical tabular ML** with no EHR/signal/coding structure — use
  `scikit-learn` or gradient boosting directly.
- **Custom deep-learning training loops / distributed training** where you want
  full control of the loop — use `pytorch-lightning`.
- **Model-agnostic explanation as the deliverable** on an already-trained model —
  use `shap`.
- **Fine-tuning a clinical LLM** (ClinicalBERT, discharge-summary models) as a
  standalone NLP job — use `transformers`.
- **Statistical inference / hypothesis testing** on outcomes rather than
  prediction — use `statistical-analysis` or `statsmodels`.

If the data has no clinical coding, signal, or EHR structure, PyHealth's
abstractions add friction without payoff.

## The Five-Stage Pipeline

```python
from pyhealth.datasets import MIMIC4Dataset, split_by_patient, get_dataloader
from pyhealth.tasks import mortality_prediction_mimic4_fn
from pyhealth.models import Transformer
from pyhealth.trainer import Trainer, get_metrics_fn

# 1. Load a dataset and attach a prediction task -> SampleDataset
dataset = MIMIC4Dataset(root="/path/to/mimic4")
sample_dataset = dataset.set_task(mortality_prediction_mimic4_fn)

# 2. Split BY PATIENT (never by sample) to avoid leakage
train_ds, val_ds, test_ds = split_by_patient(sample_dataset, [0.7, 0.1, 0.2])
train_loader = get_dataloader(train_ds, batch_size=64, shuffle=True)
val_loader   = get_dataloader(val_ds,   batch_size=64, shuffle=False)
test_loader  = get_dataloader(test_ds,  batch_size=64, shuffle=False)

# 3. Pick a model; declare feature_keys, label_key, and mode
model = Transformer(
    dataset=sample_dataset,
    feature_keys=["conditions", "procedures", "drugs"],
    label_key="label",
    mode="binary",
)

# 4. Train, monitoring a class-imbalance-aware metric
trainer = Trainer(model=model, metrics=["pr_auc", "roc_auc", "f1"])
trainer.train(
    train_dataloader=train_loader,
    val_dataloader=val_loader,
    epochs=50,
    monitor="pr_auc",              # AUPRC for rare positives
    optimizer_params={"lr": 1e-3},
)

# 5. Evaluate: inference returns (y_true, y_prob, loss[, extra_output])
y_true, y_prob, loss = trainer.inference(test_loader)
print(get_metrics_fn(model.mode)(y_true, y_prob,
      metrics=["accuracy", "pr_auc", "roc_auc", "f1"]))
```

The `mode` string (`"binary"`, `"multiclass"`, `"multilabel"`, `"regression"`)
must match what the task emits — it selects the loss, the output head, and which
metric family `get_metrics_fn` returns.

## Non-Negotiable Correctness Rules

1. **Split by patient.** Use `split_by_patient` for clinical prediction. A
   patient in both train and test leaks future outcomes; `split_by_sample`
   inflates every metric. See `references/datasets.md`.
2. **Use the right metric keys.** They are `pr_auc`, `roc_auc`, `f1`,
   `accuracy`, `precision`, `recall` (not `pr_auc_score`). For imbalanced
   outcomes (mortality, readmission) monitor **`pr_auc`**, not `accuracy`.
3. **Calibrate before you call a probability a risk.** A 0.8 output is not an
   80% chance until calibrated. Wrap the trained model with `pyhealth.calib`.
   See `references/training-evaluation.md`.
4. **Match `mode` to the task.** Drug recommendation is `multilabel`; sleep
   staging is `multiclass`; length-of-stay is `regression`.

## Capability Reference Map

Read the file that matches the stage you are on:

- **`references/datasets.md`** — Patient / Visit / Event data model, the dataset
  catalogue (EHR, signal, imaging, text), `set_task`, `SampleDataset`, and the
  splitting / `get_dataloader` functions.
- **`references/tasks.md`** — the 20+ predefined task functions, the
  task -> `mode` mapping, and how to author a custom task function.
- **`references/models.md`** — the 30+ model catalogue, the shared constructor
  contract, and selection by task / data type / interpretability need.
- **`references/medical-coding.md`** — `InnerMap` and `CrossMap`, supported
  coding systems, ATC hierarchy handling, and dataset integration.
- **`references/preprocessing.md`** — what PyHealth preprocesses automatically,
  the knobs that actually matter (sequence length, vocabulary, normalization,
  class imbalance), and where custom processing plugs in.
- **`references/training-evaluation.md`** — the `Trainer` API, metric families,
  `pyhealth.calib` calibration + conformal prediction sets, uncertainty, fairness,
  and interpretability (RETAIN attention; `shap` for the rest).

## Installation

```bash
uv pip install pyhealth      # or: pip install pyhealth
```

Needs Python >= 3.8 and PyTorch. Deep models want a GPU; large EHR datasets want
16 GB+ RAM and tens of GB of disk. API surface (especially task classes and
processors) shifts across releases — pin a version and confirm signatures against
`pyhealth.__version__` and the official docs before relying on an exact call.

## Sibling Skills

`shap` (explanations), `pytorch-lightning` (custom loops), `transformers`
(clinical LLMs), `scikit-learn` (baselines, metrics), `statistical-analysis` /
`statsmodels` (inference), `umap-learn` (embedding visualization).
