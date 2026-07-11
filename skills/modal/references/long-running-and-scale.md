# Modal — Long-Running Jobs & Scale

Net-new patterns beyond `advanced-usage.md`: launching jobs that outlive your
local process, cutting cold starts to near-zero, scaling past one node,
coordinating workers with distributed state, and reusing sandbox environments.

Portions adapted from openscience (Apache-2.0). APIs updated to current Modal
(client `>=0.73`); several openscience snippets used deprecated forms and are
corrected below.

## Disconnect-safe long-running jobs (CRITICAL)

When you launch work from `@app.local_entrypoint()` with `.remote()` or
`.spawn()`, the run is tied to your **local** process. If that process dies —
closed laptop, dropped SSH, killed terminal, crashed agent — Modal tears down the
app context and kills the function, even though it was executing in the cloud.
This is the top cause of lost multi-hour training runs.

The fix: `modal deploy` the app once (it then persists independently of your
machine), then trigger it *by name* so the trigger is fire-and-forget.

Anti-pattern — dies with your terminal:

```python
@app.local_entrypoint()
def main():
    train.spawn()   # tied to THIS process — never use for long jobs
```

Disconnect-safe pattern:

```python
# train.py — no local_entrypoint needed
import modal

app = modal.App("grpo-training")
vol = modal.Volume.from_name("checkpoints", create_if_missing=True)
image = modal.Image.debian_slim(python_version="3.11").uv_pip_install(
    "torch", "transformers", "trl"
)

@app.function(gpu="H100:4", image=image, volumes={"/ckpt": vol}, timeout=86400)
def train(config: dict | None = None):
    config = config or {}
    ...                 # runs entirely in Modal's cloud
    vol.commit()        # persist checkpoints
    return {"status": "done"}
```

```bash
modal deploy train.py          # persists independently of your machine
```

```python
# launch.py — fire-and-forget; safe to close the terminal afterwards
import modal

fn = modal.Function.from_name("grpo-training", "train")   # NOT Function.lookup (deprecated)
handle = fn.spawn({"lr": 1e-5, "epochs": 3})
print("call id:", handle.object_id)
```

Monitor from anywhere with `modal app logs grpo-training`. Retrieve the result
later with `handle.get()`; persist `handle.object_id` if you need to reconnect
from a different process.

| Launch method | Survives local disconnect? | Use for |
|---------------|----------------------------|---------|
| `modal run script.py` | No | quick tests (<5 min) |
| `local_entrypoint()` + `.remote()`/`.spawn()` | No | interactive dev, short jobs |
| `modal deploy` + `Function.from_name().spawn()` | **Yes** | training, batch, anything >5 min |
| `modal deploy` + REST/webhook trigger | **Yes** | CI/CD, automated pipelines |

## Memory snapshots (near-zero cold starts)

Snapshot a container after model load so later cold starts restore from the
snapshot instead of re-loading weights. Mark the expensive init with
`@modal.enter(snap=True)`; a plain `@modal.enter()` runs *after* the snapshot and
is not captured. Snapshotting GPU memory needs the experimental flag.

```python
@app.cls(
    gpu="H100",
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},  # required to snapshot GPU state
    scaledown_window=300,   # current name for container_idle_timeout
    image=image,
)
class FastInference:
    @modal.enter(snap=True)          # captured in the snapshot
    def load(self):
        from transformers import pipeline
        self.pipe = pipeline(model="Qwen/Qwen3-1.7B", device_map="cuda")

    @modal.method()
    def generate(self, prompt: str) -> str:
        return self.pipe(prompt)[0]["generated_text"]
```

Snapshots are cache-keyed on code/inputs; change a sentinel constant to
invalidate. Build them by deploying (`modal deploy`) — snapshots are not produced
by `modal run`. Invoke a deployed snapshotted class with
`modal.Cls.from_name(app_name, "FastInference")`.

## Multi-node clustered training (beta)

For jobs bigger than one node (8 GPUs), use the `@modal.experimental.clustered`
decorator to gang-schedule several containers on an RDMA-enabled network. `size`
is the container (node) count; combine it with a per-node `gpu="H100:8"` spec.

```python
import modal
import modal.experimental

@app.function(gpu="H100:8", timeout=86400,
              retries=modal.Retries(max_retries=10))
@modal.experimental.clustered(size=4)   # 4 nodes x 8 H100 = 32 GPUs, gang-scheduled
def train_distributed():
    info = modal.experimental.get_cluster_info()
    rank = info.rank                       # 0..world_size-1
    world_size = len(info.container_ips)
    main_addr = info.container_ips[0]      # rendezvous host for torch.distributed
    ...
```

Modal provisions a private i6pn IPv6 network with RDMA scale-out; all nodes start
together (gang scheduling). Feed `rank` / `world_size` / `main_addr` into
`torch.distributed`, Accelerate, or DeepSpeed init.

> openscience showed a `cluster_size=` **function argument** — that is not the
> current API. Use the `@modal.experimental.clustered(size=N)` decorator plus
> `modal.experimental.get_cluster_info()`.

## Distributed primitives: Dict & Queue

Coordinate fan-out workers without standing up an external store.

```python
results = modal.Dict.from_name("job-results", create_if_missing=True)

@app.function()
def worker(job_id: str, data):
    results[job_id] = process(data)     # distributed key-value write

@app.function()
def collect(job_ids: list[str]):
    return {jid: results[jid] for jid in job_ids}
```

```python
tasks = modal.Queue.from_name("tasks", create_if_missing=True)

@app.function()
def producer(items):
    for item in items:
        tasks.put(item)

@app.function()
def consumer():
    while (item := tasks.get(block=True, timeout=60)) is not None:
        process(item)
```

## Sandbox snapshots & file I/O

Beyond `create` / `exec` / `terminate` (see `advanced-usage.md`), snapshot a
sandbox's filesystem into an `Image` and boot new sandboxes from it — deps
pre-installed, instant startup.

```python
sb = modal.Sandbox.create(app=app, image=image)
sb.exec("bash", "-c", "pip install pandas scikit-learn").wait()
snap = sb.snapshot_filesystem()        # returns a modal.Image
sb.terminate()

warm = modal.Sandbox.create(image=snap, app=app)   # boots with deps already present
```

Write and read files directly with `Sandbox.open`:

```python
sb = modal.Sandbox.create(app=app, image=image, volumes={"/ws": volume})
with sb.open("/ws/script.py", "w") as f:
    f.write("print('hi')")
out = sb.exec("python", "/ws/script.py").stdout.read()
```

> The current filesystem-snapshot method is `snapshot_filesystem()` (returns an
> `Image`), not the older `snapshot()` + `Sandbox.create(snapshot=...)` form.

## Parameterized classes

`modal.parameter()` gives an `@app.cls` typed constructor args, so one deployed
class serves many configurations without redefining functions.

```python
@app.cls(gpu="A100", image=image)
class ModelServer:
    model_name: str = modal.parameter()
    temperature: float = modal.parameter(default=0.7)

    @modal.enter()
    def load(self):
        self.model = load_model(self.model_name)

    @modal.method()
    def generate(self, prompt: str) -> str:
        return self.model.generate(prompt, temperature=self.temperature)

server = ModelServer(model_name="Qwen/Qwen3-8B", temperature=0.5)
print(server.generate.remote("Hello"))
```
