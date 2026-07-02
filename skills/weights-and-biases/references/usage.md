# W&B Core Usage: Tracking, Concepts & Best Practices

Detailed reference for everyday experiment tracking with `wandb`. For
hyperparameter search see `sweeps.md`, for data/model versioning see
`artifacts.md`, for framework hooks see `integrations.md`.

## Installation & Login

```bash
pip install wandb
wandb login                       # interactive; stores API key in ~/.netrc
export WANDB_API_KEY=your_key     # or set programmatically (CI, containers)
```

## Quick Start: Basic Experiment Tracking

```python
import wandb

run = wandb.init(
    project="my-project",
    config={"learning_rate": 0.001, "epochs": 10, "batch_size": 32, "architecture": "ResNet50"},
)

for epoch in range(run.config.epochs):
    train_loss = train_epoch()
    val_loss = validate()
    wandb.log({
        "epoch": epoch,
        "train/loss": train_loss,
        "val/loss": val_loss,
        "train/accuracy": train_acc,
        "val/accuracy": val_acc,
    })

wandb.finish()
```

### With PyTorch (manual loop)

```python
import torch, wandb

wandb.init(project="pytorch-demo", config={"lr": 0.001, "epochs": 10})
config = wandb.config

for epoch in range(config.epochs):
    for batch_idx, (data, target) in enumerate(train_loader):
        output = model(data)
        loss = criterion(output, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        if batch_idx % 100 == 0:
            wandb.log({"loss": loss.item(), "epoch": epoch, "batch": batch_idx})

torch.save(model.state_dict(), "model.pth")
wandb.save("model.pth")   # upload file to the run
wandb.finish()
```

## Core Concepts

### Projects and Runs

A **project** is a collection of related experiments; a **run** is a single
execution of your script.

```python
run = wandb.init(
    project="image-classification",
    name="resnet50-experiment-1",   # optional run name
    tags=["baseline", "resnet"],     # organize / filter
    notes="First baseline run",
)
print(run.id, run.url)
```

### Configuration Tracking

```python
config = {
    "model": "ResNet50", "pretrained": True,
    "learning_rate": 0.001, "batch_size": 32, "epochs": 50, "optimizer": "Adam",
    "dataset": "ImageNet", "augmentation": "standard",
}
wandb.init(project="my-project", config=config)
lr = wandb.config.learning_rate
```

### Metric Logging

```python
wandb.log({"loss": 0.5, "accuracy": 0.92})                 # scalars
wandb.log({"loss": loss}, step=global_step)                # custom x-axis
wandb.log({"examples": [wandb.Image(img) for img in imgs]})# media
wandb.log({"gradients": wandb.Histogram(gradients)})       # histogram

table = wandb.Table(columns=["id", "prediction", "ground_truth"])
wandb.log({"predictions": table})                          # tables
```

Use `/`-separated keys (`train/loss`, `val/loss`) to group panels in the UI.

### Model Checkpointing

Prefer Artifacts over `wandb.save` for versioned, lineage-tracked checkpoints
(see `artifacts.md`):

```python
artifact = wandb.Artifact("model", type="model")
artifact.add_file("checkpoint.pth")
wandb.log_artifact(artifact)
```

## Visualization & Analysis

```python
import matplotlib.pyplot as plt
fig, ax = plt.subplots(); ax.plot(x, y)
wandb.log({"custom_plot": wandb.Image(fig)})

wandb.log({"conf_mat": wandb.plot.confusion_matrix(
    probs=None, y_true=ground_truth, preds=predictions, class_names=class_names)})
```

**Reports** (built in the W&B UI) combine runs, charts, and markdown into a
shareable, embeddable document for team collaboration.

## Best Practices

1. **Organize with tags / groups / job_type**

   ```python
   wandb.init(project="my-project", tags=["baseline", "resnet50"],
              group="resnet-experiments", job_type="train")
   ```

2. **Log everything relevant** — system metrics (`gpu/util`, `gpu/memory`),
   `git_commit`, dataset split sizes.

3. **Use descriptive run names** — `bert-base-lr0.001-bs32-epoch10`, not `run1`.

4. **Save important artifacts** — final model + a predictions `wandb.Table`
   for error analysis.

5. **Offline mode for unstable connections**

   ```python
   import os; os.environ["WANDB_MODE"] = "offline"
   # ... run ...  then later:  wandb sync <run_directory>
   ```

## Team Collaboration

- Every run is shareable via `run.url`.
- Create a team at wandb.ai, add members, set project visibility, and use
  team-level artifacts + model registry.

## Pricing (subject to change — verify at wandb.ai/pricing)

- **Free / Personal**: unlimited public projects, limited storage.
- **Academic**: free for students and researchers.
- **Teams / Enterprise**: per-seat private projects, more storage, on-prem
  (W&B Server) options.
