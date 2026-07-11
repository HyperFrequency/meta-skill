# Checkpoint-resume and volume discipline

Modal can preempt a worker and restart the container on a different machine at any time. Without
checkpointing, a preemption near the end of a long run wipes out all progress. The fix is to
persist state to a Modal volume periodically and resume from it on startup.

## The reload / commit ordering rule

A Modal volume is not automatically in sync inside a running container. Two calls bracket every
durable read/write:

- `volume.reload()` **before reading** — pulls the latest committed state into the container, so
  you see checkpoints written by a previous (preempted) run.
- `volume.commit()` **after writing** — flushes your writes to the volume so they survive the
  container. Data written but not committed is lost on preemption.

Get this ordering wrong and you either read a stale/missing checkpoint (no `reload`) or lose the
checkpoint you thought you saved (no `commit`).

## Startup: resume if a checkpoint exists

```python
import os, torch

CKPT_PATH = f"{OUT}/resume_checkpoint.pt"

volume.reload()                                   # see checkpoints from a prior preempted run
if os.path.exists(CKPT_PATH):
    ckpt = torch.load(CKPT_PATH, weights_only=False, map_location=DEVICE)
    model.load_state_dict(ckpt["model"])
    optimizer.load_state_dict(ckpt["optimizer"])
    scheduler.load_state_dict(ckpt["scheduler"])
    start_epoch = ckpt["epoch"] + 1
    train_losses = ckpt["train_losses"]
    best_metric = ckpt["best_metric"]
    print(f"Resumed at epoch {start_epoch}")
else:
    start_epoch = 1
    train_losses, best_metric = [], None
```

`weights_only=False` is required here: on torch ≥2.6 the default flipped to `True`, which loads
only tensors and refuses the optimizer/scheduler/Python objects in a full training checkpoint.
Only pass `weights_only=False` to checkpoints you produced/trust — it unpickles arbitrary objects.

## During training: save every N epochs

```python
for epoch in range(start_epoch, EPOCHS + 1):
    # ... training loop, updating train_losses / best_metric ...

    if epoch % CHECKPOINT_EVERY == 0:
        torch.save({
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "train_losses": train_losses,
            "best_metric": best_metric,
        }, CKPT_PATH)
        volume.commit()                           # persist — max lost progress = 1 interval
```

**Choosing the interval.** Maximum lost progress on preemption equals your checkpoint interval, so
pick it from epoch cost, not a round number: at ~30 s/epoch, a 10-epoch interval risks ~5 minutes;
at ~10 min/epoch, checkpoint every epoch. Balance against the fact that each `commit()` has I/O
overhead — don't commit multiple times per second.

Save what you need to *resume*, not just *inference*: model **and** optimizer **and** scheduler
state, the epoch counter, and any running metrics/loss history. Model weights alone cannot resume
a training run faithfully.

## Reading and downloading results from your local machine

```python
import modal
vol = modal.Volume.from_name("my-results")

for entry in vol.listdir("/"):                    # list top-level entries
    print(entry.path, entry.size)

with open("model.pt", "wb") as f:                 # stream a remote file down in chunks
    for chunk in vol.read_file("run_main/model.pt"):
        f.write(chunk)
```

Or via CLI: `modal volume ls my-results` and `modal volume get my-results run_main/model.pt ./`.

## Multi-writer race condition

`volume.commit()` calls from concurrent tasks are serialized, but their effects can still
**interleave** if two tasks write to the same directory. In a parameter sweep, give every run its
own subdirectory and its own checkpoint file (`/results/run_{param}/resume_checkpoint.pt`) so no
two containers ever write the same path. Never point multiple concurrent runs at one shared output
directory.
