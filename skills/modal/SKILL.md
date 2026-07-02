---
name: modal
description: "Serverless GPU cloud (Modal) for ML workloads — on-demand T4–B200 GPUs, infra defined in Python, auto-scaling web endpoints, batch/scheduled jobs, pay-per-second with scale-to-zero. Use when you need GPU compute or want to deploy a model as an API without managing servers. NOT for long-lived stateful pods or reserved GPUs (use RunPod / Lambda Labs), multi-cloud cost arbitrage (SkyPilot), complex multi-service clusters (Kubernetes), or pure CPU/local work that needs no cloud GPU."
version: 1.1.0
author: Orchestra Research
license: MIT
tags: [Infrastructure, Serverless, GPU, Cloud, Deployment, Modal]
dependencies: [modal>=0.73.0]
---

# Modal Serverless GPU

Router for running ML workloads on Modal's serverless GPU cloud. Quick start and
at-a-glance tables live here; detailed code lives in `references/`.

## When to use

Reach for Modal when you want GPU-intensive inference/training/batch jobs or an
auto-scaling model API without provisioning infrastructure, with pay-per-second
billing and scale-to-zero. Prototyping and cron-style jobs fit too.

Prefer something else when: you need a persistent stateful pod or reserved
capacity (RunPod, Lambda Labs), multi-cloud cost optimization (SkyPilot), a
complex multi-service architecture (Kubernetes), or the job is pure-CPU/local and
needs no cloud GPU at all.

Sibling skills in this repo: `temporal-*` for durable workflow orchestration,
`monorepo-deploy` for app deployment pipelines. Modal owns the GPU-compute layer.

## Quick start

```bash
pip install modal
modal setup   # opens a browser to authenticate
```

```python
import modal

app = modal.App("hello-gpu")

@app.function(gpu="T4")
def gpu_info():
    import subprocess
    return subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout

@app.local_entrypoint()
def main():
    print(gpu_info.remote())
```

Run with `modal run hello_gpu.py`.

## Core concepts

| Component | Purpose |
|-----------|---------|
| `App` | Container for functions and resources |
| `Function` | Serverless function with compute specs |
| `Cls` | Class-based function with lifecycle hooks (`@modal.enter`/`@modal.exit`) |
| `Image` | Container image definition (built in Python) |
| `Volume` | Persistent storage for models/data |
| `Secret` | Secure credential storage |

| Command | Description |
|---------|-------------|
| `modal run script.py` | Execute once and exit |
| `modal serve script.py` | Development with live reload |
| `modal deploy script.py` | Persistent cloud deployment (required for endpoints/schedules) |

## GPU selection

Specify GPUs as decorator strings: `gpu="A100"`, memory variant `gpu="A100-80GB"`,
multi-GPU `gpu="H100:4"` (up to 8), fallback list `gpu=["H100", "A100", "L40S"]`,
or `gpu="any"`. Append `!` (e.g. `"H100!"`) to disable auto-upgrade.

| GPU | VRAM | Best for |
|-----|------|----------|
| `T4` | 16 GB | Budget inference, small models |
| `L4` | 24 GB | Inference (Ada Lovelace) |
| `A10G` | 24 GB | Training/inference, ~3.3× faster than T4 |
| `L40S` | 48 GB | Inference, strong cost/perf |
| `A100-40GB` / `A100-80GB` | 40 / 80 GB | Large-model training |
| `H100` | 80 GB | Fastest, FP8 + Transformer Engine |
| `H200` | 141 GB | H100 successor, 4.8 TB/s bandwidth |
| `B200` | — | Blackwell architecture |

## Autoscaling & config (current parameter names)

Modal renamed several function parameters; older guides and code use the left
column. Use the right column with client `>=0.73`.

| Deprecated | Current |
|------------|---------|
| `container_idle_timeout=N` | `scaledown_window=N` |
| `keep_warm=N` | `min_containers=N` |
| `concurrency_limit=N` | `max_containers=N` |
| `allow_concurrent_inputs=N` | `@modal.concurrent(max_inputs=N)` decorator |
| `@modal.web_endpoint()` | `@modal.fastapi_endpoint()` (since v0.73.82) |
| `modal.Function.lookup(...)` | `modal.Function.from_name(...)` |

See `references/core-patterns.md` for a worked `@app.cls` + `@modal.concurrent`
warm-container example.

## Detailed references

- **[Core patterns](references/core-patterns.md)** — images, volumes, web endpoints, batching, secrets, scheduling, parallel `.map`, config, deployed-function lookup.
- **[Advanced usage](references/advanced-usage.md)** — multi-GPU/distributed training, cost optimization, sandboxes, production deployment, observability.
- **[Troubleshooting](references/troubleshooting.md)** — image builds, GPU OOM, cold starts, volumes, endpoints, secrets, scheduling, common error messages.

## Resources

- Documentation: https://modal.com/docs
- Examples: https://github.com/modal-labs/modal-examples
- Pricing: https://modal.com/pricing
- Discord: https://discord.gg/modal
