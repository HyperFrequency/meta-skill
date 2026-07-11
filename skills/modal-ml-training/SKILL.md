---
name: modal-ml-training
version: 0.1.0
description: >-
  Disconnect-safe patterns for long-running ML training on Modal's serverless GPU. Covers the
  deploy+spawn pattern that survives laptop shutdown / SSH drop (never `modal run --detach` for
  chained jobs), checkpoint-resume so a preemption costs at most one interval, PyTorch/CUDA
  version pinning, volume reload/commit discipline, GPU sizing + cost estimation, and fan-out
  parameter sweeps. Use for any GPU training run over ~30 min where losing progress is
  expensive, or when a job must outlive the terminal that launched it. NOT for general Modal
  usage — inference endpoints, sandboxes, batch, provisioning (use `modal`); NOT for multi-node
  distributed training (use `accelerate`, `deepspeed`, `ray-train`); NOT for reserved/stateful
  GPUs (use `lambda-labs`, `skypilot`); NOT the build-vs-buy cost decision (use
  `model-economics`).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# Modal ML Training

## Overview

Long training runs on serverless GPU have a failure mode that short jobs do not: the run can
easily outlive the laptop, SSH session, or CI step that launched it, and the container itself
can be preempted and restarted on a different machine mid-run. This skill is the disconnect-safe
discipline for that case. Two techniques carry most of the weight:

1. **Deploy + spawn** — decouple the job from your local process so closing the terminal (or
   losing the network) does not kill training.
2. **Checkpoint-resume** — persist state to a Modal volume periodically so a preemption or
   restart costs at most one checkpoint interval instead of the whole run.

Everything else here (version pinning, volume commit/reload ordering, GPU sizing, cost math,
parameter sweeps) exists to keep those two working reliably. For general Modal usage — image
building, web endpoints, sandboxes, cron, provisioning — use the `modal` skill; this one is the
narrow long-training slice.

## When to Use This Skill

- GPU training that runs longer than ~30 minutes, where re-running from scratch is expensive.
- A job that must survive laptop sleep/shutdown, SSH disconnect, or a CI runner timing out.
- Training on Modal's preemptible workers, where the container can be moved between machines.
- Fanning out one training function across many hyperparameters/datasets as parallel spawns.
- Any single-GPU (or single-container) run where you want progress to be durable.

## When NOT to Use This Skill

- **General Modal work** — inference endpoints, sandboxes, scheduled/batch jobs, image building,
  or provisioning GPUs → use `modal`.
- **Multi-node / model-parallel distributed training** — sharding one model across many GPUs →
  use `accelerate`, `deepspeed`, `ray-train`, or `pytorch-fsdp2`. This skill assumes one
  container per run.
- **Reserved, long-lived, or stateful GPU pods** — use `lambda-labs` or `skypilot`.
- **Squeezing throughput out of the GPU** (kernels, precision, batching) → use `optimize-for-gpu`.
- **Deciding whether to train at all** (build-vs-buy, ROI) → use `model-economics`.
- Short jobs (<30 min) where `modal run` in the foreground is simply fine.

## The deploy + spawn pattern (the core technique)

Do **not** use `modal run --detach` for a long job that chains operations. The detached local
process can die, and any follow-up `.remote()` calls that were going to run after it never
execute. Instead, put the entire job in one self-contained function, `modal deploy` it once, then
`spawn()` it fire-and-forget:

```python
# train_script.py
import modal

app = modal.App("my-training")
volume = modal.Volume.from_name("my-results", create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch==2.4.1", "numpy==1.26.4",   # PIN versions — see version pinning below
)

@app.function(gpu="A10G", image=image, volumes={"/results": volume}, timeout=86400)
def train():
    # Everything self-contained: download, train, checkpoint, evaluate, save.
    volume.commit()
    return results
```

```bash
modal deploy train_script.py          # one-time; the app now lives on Modal
python -c "import modal; modal.Function.from_name('my-training','train').spawn()"
# terminal can now close — the run continues on Modal
```

`spawn()` returns instantly with a call handle; the work runs remotely and independently. Use
`modal.Function.from_name(app, fn)` — the old `modal.Function.lookup(...)` was removed. Full
walkthrough (function anatomy, spawning with args, retrieving results, and the parallel
parameter-sweep fan-out) is in `references/deploy-spawn.md`.

## Checkpoint-resume (survive preemption)

Modal can preempt a worker and restart it elsewhere. Make progress durable: `reload()` the volume
on startup to look for a checkpoint, and after saving, `commit()` so it actually persists.

```python
volume.reload()                        # BEFORE reading: get the latest volume state
if os.path.exists(CKPT_PATH):
    ckpt = torch.load(CKPT_PATH, weights_only=False, map_location=DEVICE)
    # restore model / optimizer / scheduler / epoch / metrics ...

# ... every N epochs:
torch.save({...}, CKPT_PATH)
volume.commit()                        # AFTER writing: persist to the volume
```

Maximum lost progress equals your checkpoint interval — pick it against epoch cost, not a round
number. Note `weights_only=False` is required to reload optimizer/scheduler state on torch ≥2.6
(the default flipped to `True`). Full resume block, what to save, volume commit/reload ordering,
and the multi-writer race warning are in `references/checkpointing.md`.

## Version pinning (avoid `CUDA driver too old`)

Modal's GPU nodes may carry different CUDA driver versions. Unpinned `pip_install("torch")` grabs
the newest wheel, which can require a newer driver than the node has. Pin torch (and numpy —
2.0 breaks some code) to a known-compatible version:

```python
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch==2.4.1", "torchvision==0.19.1", "numpy==1.26.4",
)
```

## Picking a GPU and estimating cost

Rough rule: fit weights + activations + optimizer state + a real batch in VRAM, then pick the
cheapest GPU that clears it (T4 16 GB → small/inference, A10G 24 GB → standard training, A100/H100
40–80 GB → large models or big batches). Cost is `(seconds/epoch × epochs / 3600) × $/hr`. The
GPU table, a memory-sizing heuristic, the cost template, and the full pitfalls table live in
`references/gpu-cost-pitfalls.md`. **GPU prices drift — treat the table as approximate and verify
current rates before quoting.**

## References

- `references/deploy-spawn.md` — the deploy+spawn pattern in full: self-contained function
  anatomy, `spawn()` with arguments, retrieving results, the `--detach` failure mode, monitoring
  (`modal app list` / `logs` / `stop`), and the parallel parameter-sweep fan-out with per-run
  output subdirectories.
- `references/checkpointing.md` — complete checkpoint-resume block, what state to save, the
  `reload()`-before-read / `commit()`-after-write ordering, volume read/download from local, and
  the multi-writer race condition.
- `references/gpu-cost-pitfalls.md` — GPU selection table, VRAM sizing heuristic, cost-estimation
  template, and the full common-pitfalls table (symptom → fix).
