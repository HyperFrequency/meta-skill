---
name: weights-and-biases
description: "Track and version ML experiments with the W&B (wandb) Python SDK — automatic metric/config logging, real-time dashboards, run comparison, Bayesian/grid/random hyperparameter sweeps, dataset+model artifacts with lineage, and model registry. Integrates with PyTorch, Lightning, HuggingFace Transformers, Keras/TF, fastai, XGBoost/LightGBM. Use when you need to log training runs, compare experiments, tune hyperparameters, or version models/datasets. Do NOT use for distributed compute/orchestration (use Dask/Ray), pure local plotting with no run tracking (use matplotlib/seaborn), the training framework itself, generic backtesting/quant tearsheets, or non-ML data pipelines. For self-hosted MLflow-style stacks the API differs — this skill targets wandb."
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [MLOps, Weights And Biases, WandB, Experiment Tracking, Hyperparameter Tuning, Model Registry, Artifacts, PyTorch, HuggingFace]
dependencies: [wandb]
---

# Weights & Biases (wandb): ML Experiment Tracking & MLOps

## What

Weights & Biases is a collaborative MLOps platform. The `wandb` Python SDK logs
metrics, configs, media, and artifacts from training runs to a hosted (or
self-hosted) dashboard for real-time visualization, comparison, hyperparameter
sweeps, and model/dataset versioning.

## When to use

- Track ML experiments with automatic metric and hyperparameter logging.
- Visualize training in real time and compare runs across configs.
- Optimize hyperparameters with automated sweeps (Bayesian/grid/random).
- Version datasets and models with lineage via Artifacts + model registry.
- Add experiment tracking to PyTorch, Lightning, HuggingFace, Keras, fastai,
  or XGBoost/LightGBM training.

## When NOT to use

- Distributed compute / job orchestration — use Dask, Ray, or a scheduler.
- Pure local plotting with no run tracking — use matplotlib/seaborn.
- As a training framework — wandb only observes/logs; it does not train.
- Generic quant backtesting or tearsheets — use the quant skills.
- Non-ML data pipelines/ETL.

## Minimal example

```python
import wandb

run = wandb.init(project="my-project", config={"lr": 1e-3, "epochs": 10})
for epoch in range(run.config.epochs):
    wandb.log({"train/loss": train_loss, "val/accuracy": val_acc})
wandb.finish()
```

```bash
pip install wandb && wandb login   # or: export WANDB_API_KEY=...
```

## Core API at a glance

| Need | Call |
|------|------|
| Start a run | `wandb.init(project=, config=, name=, tags=, group=)` |
| Log metrics/media | `wandb.log({...})`, `wandb.Image`, `wandb.Table`, `wandb.Histogram` |
| Access hyperparams | `wandb.config.<key>` |
| End a run | `wandb.finish()` |
| Version data/model | `wandb.Artifact(...)` + `wandb.log_artifact(...)` |
| Hyperparameter search | `wandb.sweep(config)` + `wandb.agent(sweep_id, fn, count=)` |
| Framework auto-log | `report_to="wandb"` (HF), `WandbLogger` (Lightning), callbacks |

## References

- `references/usage.md` — installation, quick start, core concepts (runs,
  config, metric logging, checkpoints), visualization, best practices,
  collaboration, pricing.
- `references/sweeps.md` — comprehensive hyperparameter optimization guide.
- `references/artifacts.md` — dataset/model versioning, lineage, model registry.
- `references/integrations.md` — framework-specific examples (HuggingFace,
  Lightning, Keras/TF, fastai, XGBoost/LightGBM, PyTorch native).

## Resources

- Docs: https://docs.wandb.ai
- GitHub: https://github.com/wandb/wandb
- Examples: https://github.com/wandb/examples
