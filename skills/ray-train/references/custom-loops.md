# Custom Ray Train Training Loops

The `train_func` you pass to a `Trainer` *is* the per-worker training loop. Ray
runs one copy on each distributed worker, sets up the process group, and gives
you a small session API to coordinate, report metrics, and checkpoint.

> API note: verified against Ray 2.x (2.40+). The current namespace is
> `ray.train` (e.g. `ray.train.report`, `ray.train.get_context`,
> `ray.train.Checkpoint`, `ray.train.torch.prepare_model`). Older guides that
> import `from ray import train` and call `train.report` still work but the
> fully-qualified `ray.train.*` form is canonical.

## Anatomy of a worker loop (PyTorch)

```python
import os, tempfile
import torch
import ray.train.torch
from ray.train.torch import TorchTrainer
from ray.train import ScalingConfig, Checkpoint

def train_func(config):
    # 1. Build model/optimizer normally — no manual .cuda() needed.
    model = MyModel()
    optimizer = torch.optim.Adam(model.parameters(), lr=config["lr"])

    # 2. prepare_model wraps in DDP and moves to the worker's device.
    model = ray.train.torch.prepare_model(model)

    # 3. prepare_data_loader injects a DistributedSampler + device transfer.
    train_loader = ray.train.torch.prepare_data_loader(build_loader())

    for epoch in range(config["epochs"]):
        # Reshuffle shards each epoch when running multi-worker.
        if ray.train.get_context().get_world_size() > 1:
            train_loader.sampler.set_epoch(epoch)

        for batch in train_loader:
            loss = compute_loss(model, batch)  # batch already on device
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # 4. Report + checkpoint once per epoch (see below).
        report_and_checkpoint(model, optimizer, epoch, loss)

trainer = TorchTrainer(
    train_func,
    train_loop_config={"lr": 1e-3, "epochs": 10},
    scaling_config=ScalingConfig(num_workers=8, use_gpu=True),
)
result = trainer.fit()
```

## The worker session context

`ray.train.get_context()` exposes per-worker coordination info:

| Method | Returns |
| --- | --- |
| `get_world_size()` | Total number of workers |
| `get_world_rank()` | Global rank of this worker (0..world_size-1) |
| `get_local_rank()` | Rank within this node (use to pin a GPU) |
| `get_node_rank()` | Rank of this worker's node |

Use rank checks to do work exactly once (logging, dataset download to a shared
path, printing) instead of `world_size` times:

```python
if ray.train.get_context().get_world_rank() == 0:
    print(metrics)
```

## Reporting metrics and checkpoints (current API)

The idiomatic pattern saves into a temp dir, wraps it as a `Checkpoint`, and
passes it alongside metrics to a single `ray.train.report` call. Ray persists
the checkpoint to the run's `storage_path` and aggregates metrics.

```python
def report_and_checkpoint(model, optimizer, epoch, loss):
    metrics = {"loss": loss.item(), "epoch": epoch}
    with tempfile.TemporaryDirectory() as tmp:
        # model.module unwraps the DDP wrapper added by prepare_model.
        torch.save(
            {"model": model.module.state_dict(),
             "optimizer": optimizer.state_dict(),
             "epoch": epoch},
            os.path.join(tmp, "ckpt.pt"),
        )
        ray.train.report(
            metrics,
            checkpoint=Checkpoint.from_directory(tmp),
        )
```

Only rank 0's checkpoint needs to be uploaded in data-parallel training, but
calling `report` on every worker (with the same metrics) is required so all
workers stay in lockstep — Ray handles deduplication of the persisted artifact.

## Resuming from a checkpoint (fault tolerance)

On worker restart, `ray.train.get_checkpoint()` returns the latest checkpoint so
the loop can resume mid-run:

```python
def train_func(config):
    model = MyModel()
    optimizer = torch.optim.Adam(model.parameters())
    start_epoch = 0

    checkpoint = ray.train.get_checkpoint()
    if checkpoint:
        with checkpoint.as_directory() as ckpt_dir:
            state = torch.load(os.path.join(ckpt_dir, "ckpt.pt"))
            model.load_state_dict(state["model"])
            optimizer.load_state_dict(state["optimizer"])
            start_epoch = state["epoch"] + 1

    model = ray.train.torch.prepare_model(model)
    for epoch in range(start_epoch, config["epochs"]):
        ...
```

Configure how many times Ray retries failed workers via the Trainer's
`run_config`:

```python
from ray.train import RunConfig, FailureConfig
run_config = RunConfig(failure_config=FailureConfig(max_failures=3))
```

## Loading the final model after `fit()`

```python
result = trainer.fit()
with result.checkpoint.as_directory() as ckpt_dir:
    state = torch.load(os.path.join(ckpt_dir, "ckpt.pt"))
    model = MyModel()
    model.load_state_dict(state["model"])
```

## Other backends / framework-agnostic loops

The same session API (`report`, `get_context`, `get_checkpoint`, `Checkpoint`)
works for every Ray Train backend — only the `prepare_*` helpers and Trainer
class change:

- **TensorFlow**: `TensorflowTrainer`; wrap the model build inside
  `ray.train.tensorflow.prepare_dataset_shard` and a `MultiWorkerMirroredStrategy`
  scope provided by `ray.train.tensorflow`.
- **XGBoost / LightGBM**: `XGBoostTrainer` / `LightGBMTrainer` — pass datasets and
  params, no manual loop needed.
- **HuggingFace Transformers**: write a normal `transformers.Trainer` loop inside
  `train_func` and add `ray.train.huggingface.transformers.prepare_trainer(trainer)`
  before `trainer.train()`.
- **Fully custom**: any framework works as long as you (1) read hyperparameters
  from `config`, (2) call `ray.train.report` to surface metrics/checkpoints, and
  (3) read `ray.train.get_checkpoint()` to resume. Ray only manages process
  groups and scheduling — the loop body is yours.
```