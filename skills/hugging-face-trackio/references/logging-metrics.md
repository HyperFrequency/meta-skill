# Logging Metrics with Trackio (Python API)

Trackio gives a wandb-compatible, local-first API for recording ML training
metrics. Metrics land in a local SQLite database by default; a `space_id`
mirrors them to a Hugging Face Space for a persistent dashboard.

- GitHub: [gradio-app/trackio](https://github.com/gradio-app/trackio)
- Docs: [huggingface.co/docs/trackio](https://huggingface.co/docs/trackio/index)

## Install

```bash
pip install trackio
# or
uv pip install trackio
```

## Core functions

| Function | Purpose |
|----------|---------|
| `trackio.init(...)` | Start a new tracking run |
| `trackio.log(dict)` | Log a dict of metrics (call repeatedly during training) |
| `trackio.finish()` | Finalize the run and flush all metrics |
| `trackio.show()` | Launch the local dashboard |
| `trackio.sync(...)` | Sync a local project to a Hugging Face Space |

## Basic usage

```python
import trackio

trackio.init(project="my-project", config={"learning_rate": 0.001, "epochs": 10})

for epoch in range(10):
    loss = train_epoch()
    trackio.log({"loss": loss, "epoch": epoch})

trackio.finish()
```

## `trackio.init()` parameters

```python
trackio.init(
    project="my-project",         # groups runs together
    name="run-name",              # optional: name for this specific run
    config={...},                 # hyperparameters / static config to record
    space_id="username/trackio",  # optional: mirror to an HF Space dashboard
    dataset_id="username/runs",   # optional: also persist to an HF Dataset (synced ~every 5 min)
    group="experiment-group",     # optional: group related runs in the sidebar
    resume="never",               # optional: resume an existing run instead of starting fresh
)
```

## Local vs remote dashboard

### Local (default)

Metrics go to a local SQLite database; view them by launching the dashboard.

```python
trackio.init(project="my-project")
# ... training ...
trackio.finish()
trackio.show()   # or, from a terminal: trackio show --project my-project
```

### Remote (Hugging Face Space)

Pass `space_id` to mirror metrics to a Space, which is auto-created if it does
not exist. This yields a persistent, shareable dashboard.

```python
trackio.init(project="my-project", space_id="username/trackio")
```

> For remote training (cloud GPUs, HF Jobs, etc.) **always** set `space_id`.
> Local storage is destroyed when the instance terminates, taking un-synced
> metrics with it.

### Sync an existing local project

```python
trackio.sync(project="my-project", space_id="username/my-experiments")
```

Syncing to a Space requires Hugging Face Hub credentials (install
`huggingface-hub`; authenticate via `huggingface-cli login` or an `HF_TOKEN`
environment variable).

## wandb compatibility

The scalar `init`/`log`/`finish` path mirrors wandb, so importing under the
`wandb` alias makes Trackio a drop-in replacement for that surface:

```python
import trackio as wandb

wandb.init(project="my-project")
wandb.log({"loss": 0.5})
wandb.finish()
```

Do not assume advanced wandb features (artifacts, sweeps, rich media) map over —
verify against the Trackio docs before relying on them.

## TRL / Transformers integration

Set `report_to="trackio"` on a TRL/Transformers trainer config and logging is
automatic — no manual `log()` calls needed inside the loop.

```python
from trl import SFTConfig, SFTTrainer
import trackio

trackio.init(
    project="sft-training",
    space_id="username/trackio",
    config={"model": "Qwen/Qwen2.5-0.5B", "dataset": "trl-lib/Capybara"},
)

config = SFTConfig(output_dir="./output", report_to="trackio")  # + other args
trainer = SFTTrainer(model=model, args=config, ...)
trainer.train()
trackio.finish()
```

With this integration Trackio typically captures training loss, learning rate,
evaluation metrics, and throughput automatically. For manual logging, log any
numeric metrics:

```python
trackio.log({
    "train_loss": 0.5,
    "train_accuracy": 0.85,
    "val_loss": 0.4,
    "val_accuracy": 0.88,
    "epoch": 1,
})
```

## Grouping runs

Use `group` to organize related runs in the dashboard sidebar — e.g. by
experiment arm or by swept hyperparameter:

```python
trackio.init(project="my-project", name="baseline-v1", group="baseline")
trackio.init(project="my-project", name="augmented-v1", group="augmented")

trackio.init(project="hyperparam-sweep", name="lr-0.001", group="lr_0.001")
trackio.init(project="hyperparam-sweep", name="lr-0.01",  group="lr_0.01")
```

## Config best practices

Keep `config` minimal — record only what is useful for comparing runs:

```python
trackio.init(
    project="qwen-sft-capybara",
    name="baseline-lr2e5",
    config={
        "model": "Qwen/Qwen2.5-0.5B",
        "dataset": "trl-lib/Capybara",
        "learning_rate": 2e-5,
        "num_epochs": 3,
        "batch_size": 8,
    },
)
```

## Embedding Space dashboards

Embed a Space dashboard in a web page with an `<iframe>` and query parameters:

```html
<iframe
  src="https://username-trackio.hf.space/?project=my-project&metrics=train_loss,val_loss&sidebar=hidden"
  style="width:1600px; height:500px; border:0;">
</iframe>
```

Query parameters:

- `project` — filter to a specific project
- `metrics` — comma-separated metric names to display
- `sidebar` — `hidden` or `collapsed`
- `smoothing` — 0-20 (smoothing slider value)
- `xmin`, `xmax` — x-axis limits
