---
name: tensorboard
description: Visualize and debug ML training with TensorBoard - log scalars (loss/accuracy), histograms (weights/gradients), images, embeddings, model graphs, and hyperparameter sweeps, then compare runs and profile performance in the browser dashboard. Works with PyTorch (torch.utils.tensorboard.SummaryWriter), TensorFlow/Keras (TensorBoard callback), Lightning, and HuggingFace. Use WHEN you need a local, free, self-hosted way to inspect training curves, diagnose vanishing/exploding gradients, project embeddings (PCA/t-SNE/UMAP), or find GPU/data-loading bottlenecks. Use WHEN tracking a few experiments on one machine. Do NOT use for team experiment management, model registries, artifact versioning, or hosted dashboards (use Weights & Biases, MLflow, or Neptune); for hyperparameter optimization search itself (use Optuna/Ray Tune - TensorBoard only visualizes results); for non-ML general plotting (use matplotlib/seaborn); or for production model monitoring/alerting (use Evidently/Prometheus).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [MLOps, TensorBoard, Visualization, Training Metrics, Model Debugging, PyTorch, TensorFlow, Experiment Tracking, Performance Profiling]
dependencies: [tensorboard, torch, tensorflow]
---

# TensorBoard: Visualization Toolkit for ML

TensorBoard is Google's open-source (Apache 2.0) dashboard for inspecting ML training. It reads event log files written during training and serves interactive charts at `http://localhost:6006`. This file is a concise router; deep examples live in `references/`.

## When to Use This Skill

- **Visualize training metrics** (loss, accuracy, learning rate) over steps/epochs
- **Debug models** with weight/gradient/activation histograms and distributions
- **Compare experiments** across multiple runs in one dashboard
- **Visualize model graphs**, images, text, and PR curves
- **Project embeddings** to 2D/3D (PCA, t-SNE, UMAP)
- **Track hyperparameter** sweeps (HParams tab)
- **Profile performance** to find GPU/data-loading bottlenecks (Profile tab)

## When NOT to Use

- **Team experiment management, model registry, artifact/dataset versioning, or a hosted dashboard** → use Weights & Biases, MLflow, or Neptune.
- **Running the hyperparameter search itself** → use Optuna or Ray Tune; TensorBoard only *visualizes* the results.
- **General non-ML plotting / publication figures** → use matplotlib or seaborn.
- **Production model monitoring, drift detection, or alerting** → use Evidently, Prometheus/Grafana.

## Installation

```bash
pip install tensorboard                       # standalone
pip install torch torchvision tensorboard     # PyTorch integration
pip install tensorflow                         # TensorFlow (TensorBoard bundled)

tensorboard --logdir=runs                      # launch -> http://localhost:6006
```

## Quick Start

### PyTorch

```python
from torch.utils.tensorboard import SummaryWriter

writer = SummaryWriter('runs/experiment_1')
for epoch in range(10):
    writer.add_scalar('Loss/train', train_epoch(), epoch)
    writer.add_scalar('Accuracy/val', validate(), epoch)
writer.close()
# tensorboard --logdir=runs
```

### TensorFlow / Keras

```python
import tensorflow as tf

tb = tf.keras.callbacks.TensorBoard(log_dir='logs/fit', histogram_freq=1)
model.fit(x_train, y_train, epochs=10,
          validation_data=(x_val, y_val), callbacks=[tb])
# tensorboard --logdir=logs
```

## Core API Map

PyTorch `SummaryWriter` methods (mirror as `tf.summary.*` under a `create_file_writer().as_default()` context):

| Goal | PyTorch method | TensorFlow equivalent |
|------|----------------|------------------------|
| Single metric | `add_scalar(tag, value, step)` | `tf.summary.scalar` |
| Grouped metrics | `add_scalars(group, {tag: val}, step)` | multiple writers |
| Image / grid | `add_image(tag, chw_tensor, step)` | `tf.summary.image` |
| Weight/grad distribution | `add_histogram(tag, tensor, step)` | `tf.summary.histogram` |
| Model architecture | `add_graph(model, dummy_input)` | `write_graph=True` callback |
| Embedding projector | `add_embedding(mat, metadata, label_img, global_step)` | `embeddings_freq` callback |
| Hyperparam sweep | `add_hparams({hp}, {metric})` | `hp.hparams` (tensorboard.plugins.hparams) |
| Text / markdown | `add_text(tag, str, step)` | `tf.summary.text` |
| PR curve | `add_pr_curve(tag, labels, preds, global_step)` | via `tensorboard.plugins.pr_curve` |

Always `writer.flush()`/`writer.close()` (or use `with SummaryWriter(...) as writer:`) so events are persisted.

## Key Practices

- **Descriptive run dirs**: `runs/resnet50_lr0.001_bs32_{timestamp}` beats auto-generated names.
- **Group tags with `/`**: `Loss/train`, `Loss/val` so charts share an axis.
- **Separate writers** for train vs. val: `runs/exp1/train`, `runs/exp1/val`.
- **Log epoch metrics always, batch metrics sparingly** (e.g. every 100 batches) to keep log files small.
- **Compare runs** by pointing `--logdir` at the parent directory; toggle/filter runs (regex) in the UI.

## References

Load these for full, copy-pasteable patterns:

- [`references/visualization.md`](references/visualization.md) — scalars, images, attention maps, histograms (weights/activations/gradients), graphs, embedding projector, PR curves, text/markdown.
- [`references/profiling.md`](references/profiling.md) — PyTorch `torch.profiler` + `tensorboard_trace_handler`, TF Profiler, GPU utilization, memory profiling, bottleneck analysis.
- [`references/integrations.md`](references/integrations.md) — end-to-end loops for PyTorch (incl. DDP rank-0 logging), TF/Keras custom loops, PyTorch Lightning logger, HuggingFace `TrainingArguments`, fast.ai.

## Related Skills

- `pytorch-lightning` — training framework with a built-in TensorBoard logger.
- `umap-learn` — generate the embeddings you then explore in the Projector tab.
- `matplotlib` / `seaborn` — static figures when you don't need a live dashboard.

## External Resources

- Docs: https://www.tensorflow.org/tensorboard
- PyTorch integration: https://pytorch.org/docs/stable/tensorboard.html
- GitHub: https://github.com/tensorflow/tensorboard
