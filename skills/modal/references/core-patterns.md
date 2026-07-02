# Modal Core Patterns

Detailed code for the building blocks referenced by `SKILL.md`. All examples use
current Modal APIs (client `>=0.73`). See the deprecation table in `SKILL.md` for
the old parameter names if you hit older code.

## Container images

```python
# Basic image with pip
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "torch==2.1.0", "transformers==4.36.0", "accelerate"
)

# From CUDA base
image = modal.Image.from_registry(
    "nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04",
    add_python="3.11",
).pip_install("torch", "transformers")

# With system packages
image = modal.Image.debian_slim().apt_install("git", "ffmpeg").pip_install("openai-whisper")

# Faster installs with uv
image = modal.Image.debian_slim().uv_pip_install("torch", "transformers", "accelerate")
```

## Persistent storage (Volumes)

```python
volume = modal.Volume.from_name("model-cache", create_if_missing=True)

@app.function(gpu="A10G", volumes={"/models": volume})
def load_model():
    import os
    model_path = "/models/llama-7b"
    if not os.path.exists(model_path):
        model = download_model()
        model.save_pretrained(model_path)
        volume.commit()   # Persist writes back to the volume
    return load_from_path(model_path)
```

Call `volume.commit()` after writing and `volume.reload()` before reading to avoid
stale data. For S3/GCS use `modal.CloudBucketMount(...)` in place of a Volume.

## Web endpoints

```python
# Simple function -> POST endpoint
@app.function()
@modal.fastapi_endpoint(method="POST")   # replaces deprecated @modal.web_endpoint
def predict(text: str) -> dict:
    return {"result": model.predict(text)}
```

```python
# Full ASGI app (multiple routes)
from fastapi import FastAPI
web_app = FastAPI()

@web_app.post("/predict")
async def predict(text: str):
    return {"result": await model.predict.remote.aio(text)}

@app.function()
@modal.asgi_app()
def fastapi_app():
    return web_app
```

| Decorator | Use case |
|-----------|----------|
| `@modal.fastapi_endpoint()` | Single function → API |
| `@modal.asgi_app()` | Full FastAPI/Starlette apps |
| `@modal.wsgi_app()` | Django/Flask apps |
| `@modal.web_server(port)` | Arbitrary HTTP servers |

## Dynamic batching

```python
@app.function()
@modal.batched(max_batch_size=32, wait_ms=100)
async def batch_predict(inputs: list[str]) -> list[dict]:
    # Modal accumulates individual calls into one batched invocation
    return model.batch_predict(inputs)
```

Use `@modal.batched` for GPU throughput (group work). Use `@modal.concurrent` for
I/O-bound concurrency (handle many in-flight requests per container) — they solve
different problems and can be combined.

## Secrets

```bash
modal secret create huggingface HF_TOKEN=hf_xxx
```

```python
@app.function(secrets=[modal.Secret.from_name("huggingface")])
def download_model():
    import os
    token = os.environ["HF_TOKEN"]
```

## Scheduling

```python
@app.function(schedule=modal.Cron("0 0 * * *"))   # daily at 00:00 UTC
def daily_job():
    pass

@app.function(schedule=modal.Period(hours=1))
def hourly_job():
    pass
```

Cron expressions are evaluated in UTC. The app must be `modal deploy`-ed for
schedules to fire.

## Class lifecycle + cold-start mitigation

```python
@app.cls(
    gpu="A100",
    scaledown_window=300,   # keep a warm container up to 5 min after last input
    min_containers=1,       # always keep 1 container ready (formerly keep_warm)
)
@modal.concurrent(max_inputs=10)   # handle 10 concurrent inputs per container
class Model:
    @modal.enter()              # runs once at container start, not per request
    def load(self):
        self.model = load_model()

    @modal.method()
    def predict(self, x):
        return self.model(x)
```

## Parallel processing

```python
@app.function()
def process_item(item):
    return expensive_computation(item)

@app.function()
def run_parallel():
    items = list(range(1000))
    results = list(process_item.map(items))   # fan out to parallel containers
    return results
```

Use `.starmap()` for multi-argument items and `.remote.aio()` for async callers.

## Common configuration

```python
@app.function(
    gpu="A100",
    memory=32768,         # 32 GB RAM
    cpu=4,                # 4 CPU cores
    timeout=3600,         # 1 hour max wall-clock
    scaledown_window=120, # keep warm 2 min (formerly container_idle_timeout)
    retries=3,            # retry on failure
    max_containers=10,    # autoscaling ceiling (formerly concurrency_limit)
)
def my_function():
    pass
```

## Debugging quick checks

```python
# Run locally without provisioning a container
if __name__ == "__main__":
    result = my_function.local()
```

```bash
modal app logs my-app                       # stream logs
modal app logs my-app --function my_function
```

## Invoking a deployed function from outside

```python
import modal
fn = modal.Function.from_name("my-app", "my_function")   # replaces Function.lookup
result = fn.remote(arg1, arg2)
```
