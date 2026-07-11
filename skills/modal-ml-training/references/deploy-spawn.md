# Deploy + spawn: disconnect-safe long jobs

The goal is to make the training run independent of the process that started it. Two rules:

1. Put the **entire** job in one self-contained function — no chained `.remote()` calls that
   depend on your laptop staying alive.
2. `modal deploy` the app once, then `spawn()` the function fire-and-forget.

## Why not `modal run --detach`

`modal run --detach fn` detaches the *first* remote call, but if your script chains work — call
`train.remote()`, then `evaluate.remote()`, then `plot.remote()` — those later calls are driven by
the **local** process. If your terminal/network dies, the detached first call may finish but the
follow-ups never fire. You get a half-finished run and no error. Deploy + spawn avoids this by
making the remote function own the whole pipeline.

## Anatomy of a self-contained training function

Everything the run needs happens inside one function body: data download, training loop,
checkpointing, evaluation, and saving outputs to the volume.

```python
# train_script.py
import os
import modal

app = modal.App("my-training")
volume = modal.Volume.from_name("my-results", create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch==2.4.1", "torchvision==0.19.1", "numpy==1.26.4",
)

@app.function(
    gpu="A10G",
    image=image,
    volumes={"/results": volume},
    timeout=86400,          # 24h max; set generously so the job is not killed mid-run
)
def train():
    import torch
    OUT = "/results/run_main"
    os.makedirs(OUT, exist_ok=True)

    # 1. download data / build model  (inside the function, on the GPU node)
    # 2. checkpoint-resume startup     (see references/checkpointing.md)
    # 3. training loop with periodic torch.save(...) + volume.commit()
    # 4. final evaluate + save artifacts to OUT

    volume.commit()
    return {"status": "done", "out": OUT}
```

Key `@app.function` arguments:

- `gpu=` — `"T4"`, `"A10G"`, `"A100"`, `"A100-80GB"`, `"H100"` (see `gpu-cost-pitfalls.md`).
- `image=` — the pinned image; unpinned torch causes CUDA-driver errors.
- `volumes={mount_path: volume}` — where checkpoints/outputs land durably.
- `timeout=` — seconds; cap is 86400 (24h). Too-short timeouts kill long runs mid-epoch.

## Deploy, then spawn

```bash
modal deploy train_script.py     # registers the app on Modal; persists across sessions
```

```python
import modal
fn = modal.Function.from_name("my-training", "train")
call = fn.spawn()                # returns immediately with a FunctionCall handle
print(call.object_id)            # record this to fetch results later
```

`spawn()` is fire-and-forget: it returns a `FunctionCall` handle instantly and the work runs
remotely. Your terminal can close. To collect the return value later:

```python
call = modal.FunctionCall.from_id(object_id)
result = call.get()              # blocks until the run finishes; or get(timeout=...)
```

Note: use `modal.Function.from_name(app, fn)`. The older `modal.Function.lookup(app, fn)` was
removed in Modal ≥0.68.

## Parallel parameter sweeps (fan-out)

To run the same function across many hyperparameters/datasets, parameterize it and spawn once per
value. Each run is an independent GPU container sharing one deployed app.

```python
@app.function(gpu="A10G", image=image, volumes={"/results": volume}, timeout=86400)
def train(param_value: str):
    OUT = f"/results/run_{param_value}"     # SEPARATE subdir per run — avoids write races
    os.makedirs(OUT, exist_ok=True)
    # ... training using param_value, with its own checkpoint under OUT ...
    volume.commit()
    return {"param": param_value, "out": OUT}
```

```python
import modal
fn = modal.Function.from_name("my-sweep-app", "train")
for param in ["0.1", "0.4", "1.0", "4.0"]:
    call = fn.spawn(param)
    print(f"spawned param={param}: {call.object_id}")
```

Design rules for sweeps:

- Each run writes to its **own** subdirectory (`/results/run_{param}`) with its **own** checkpoint
  file — otherwise parallel runs clobber each other on the shared volume.
- `modal.Function.map(iterable)` is the alternative when you want to block locally and gather all
  results; `spawn()` in a loop is the right choice when you want to disconnect.
- Cost scales linearly: N parallel A10G runs cost N × the hourly rate simultaneously.

## Monitoring and stopping

```bash
modal app list                   # verify the running app count matches expected parallelism
modal app logs my-training       # stream logs in real time (sweep logs interleave across tasks)
modal app stop <app-id>          # stop a running app
```

If `modal app list` shows more running tasks than you intended, you probably spawned the same
function twice — stop the duplicates before they double your bill.
