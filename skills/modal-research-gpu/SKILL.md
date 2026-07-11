---
name: modal-research-gpu
version: 0.1.0
description: >-
  Run GPU-accelerated SCIENTIFIC computing on Modal's serverless cloud — Monte
  Carlo simulations, molecular dynamics, numerical PDE/ODE solvers, GPU linear
  algebra (CuPy/RAPIDS), differentiable modeling (JAX), massively parallel
  parameter sweeps, and large-scale scientific data processing. WHAT: define a
  Modal Image, pick a GPU tier, fan work out across many GPUs with .map(), and
  persist results to Volumes — behind a mandatory cost-approval gate before any
  paid run. WHEN: you have a compute-bound research workload that needs a GPU
  you don't have locally, or an embarrassingly-parallel simulation/sweep to
  spread across dozens of GPUs. WHEN NOT: for ML model TRAINING use
  `distributed-training` or `fine-tuning`; for model INFERENCE/serving use
  `inference-serving`; for kernel-level speedups of GPU code you already run use
  `optimize-for-gpu`; for CPU-only or small jobs, run them locally.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Modal Research GPU

## Overview

Modal is a serverless compute platform: you write ordinary Python, decorate a
function, declare the container image and GPU it needs, and Modal provisions the
hardware on demand, runs the function, and tears it down — you pay only for
wall-clock GPU seconds. This skill uses that model for **scientific computing**,
not machine learning: simulations, numerical methods, and batch data crunching
that are compute-bound and often embarrassingly parallel.

The core loop is always the same four moves: **build an Image** (pinned
scientific stack), **choose a GPU tier**, **fan out** the work with `.map()`
across many containers, and **persist** results to a Volume. Everything else in
this skill is depth on those four moves plus the discipline to not burn money.

Keep this page as the map. Deep tables, full code patterns, and image recipes
live in the reference files linked below.

## When to Use This Skill

Reach for this skill when the workload is GPU-suited scientific compute:

| Workload | Example |
|----------|---------|
| Monte Carlo simulation | Binding free energy, risk modeling, particle transport |
| Molecular dynamics | OpenMM / GROMACS / LAMMPS trajectories on GPU |
| Numerical PDE/ODE solvers | CFD, heat transfer, electromagnetics, reaction-diffusion |
| GPU linear algebra | CuPy/RAPIDS eigenproblems, SVD, large dense/sparse solves |
| Differentiable modeling | JAX/`diffrax` gradient-based fitting, inverse problems |
| Parallel parameter sweeps | Sensitivity analysis, grid/latin-hypercube exploration |
| Large-scale data processing | Genomics/imaging/signal pipelines that exceed local RAM/GPU |

The trigger is: **compute-bound, GPU-suited, and either too big for your local
machine or trivially parallel across many GPUs.**

## When NOT to Use This Skill

- **Training an ML model** → use `distributed-training` (multi-node) or
  `fine-tuning`. This skill is not for gradient-descent training loops.
- **Serving / inference** of a trained model → use `inference-serving`.
- **Kernel-level GPU optimization** of code you already run on a GPU (fusing
  ops, tuning CUDA, profiling) → use `optimize-for-gpu`. This skill *places*
  work on GPUs; it does not micro-optimize kernels.
- **CPU-only, small, or interactive** jobs → run them locally; a GPU rental adds
  cost and cold-start latency for no benefit.
- **Designing the multi-stage research pipeline** that *calls* these jobs → use
  `scientific-pipeline-builder`; wire the compute steps to this skill.
- **Turning results into figures** → hand off to `scientific-visualization`.

## Prerequisites

Install and authenticate the Modal client once:

```bash
pip install "modal>=0.73"
modal token new          # opens browser; writes ~/.modal.toml
# ...or set both in the environment for headless/CI use:
#   MODAL_TOKEN_ID, MODAL_TOKEN_SECRET
```

Sanity check without spending anything:

```bash
[ -n "$MODAL_TOKEN_ID" ] && echo "token id set" || echo "run: modal token new"
```

## The Anatomy of a Research Job

A minimal, complete job — image, GPU, remote call:

```python
import modal

app = modal.App("research-compute")

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "numpy", "scipy", "cupy-cuda12x"
)

@app.function(image=image, gpu="A10G", timeout=3600)
def gpu_compute(size: int):
    import cupy as cp  # import GPU libs INSIDE the function, not at module top
    matrix = cp.random.randn(size, size, dtype=cp.float64)
    eigenvalues = cp.linalg.eigvalsh(matrix @ matrix.T)
    return cp.asnumpy(eigenvalues)  # return host-side (picklable) arrays

@app.local_entrypoint()
def main():
    print(gpu_compute.remote(4096))   # .remote() runs it on Modal
```

Run with `modal run script.py`. Two rules that trip people up: **import
GPU/CUDA libraries inside the function body** (the local process has no CUDA),
and **return host-side objects** (`cp.asnumpy(...)`, plain dicts) because return
values are pickled back to your machine.

The scaling patterns — parallel `.map()` fan-out for Monte Carlo, molecular
dynamics from a registry image, Volume-backed parameter sweeps, JAX PDE solves,
and multi-GPU single node — are in
[references/patterns.md](references/patterns.md).

## Choosing a GPU

Start on the smallest tier that fits your problem in VRAM, verify correctness,
then scale up only if VRAM or throughput demands it.

| Tier | VRAM | Good default for |
|------|------|------------------|
| `T4` | 16 GB | Light numerics, quick tests |
| `L4` | 24 GB | Medium simulations, data processing |
| `A10G` | 24 GB | General scientific computing (**start here**) |
| `A100-40GB` | 40 GB | Large simulations, molecular dynamics |
| `A100-80GB` | 80 GB | Very large state spaces, multi-physics |
| `H100` | 80 GB | Max throughput, large-scale Monte Carlo |

GPU is a string: `gpu="A10G"`, memory-qualified `gpu="A100-80GB"`, or with a
count on a single node `gpu="A100-80GB:4"`. Full VRAM/throughput trade-offs,
current-pricing guidance, and GPU-hour estimation are in
[references/gpu-and-cost.md](references/gpu-and-cost.md).

## Cost Discipline (mandatory gate)

Modal bills per GPU-second and a fan-out can spend real money in minutes.
**Before launching ANY paid GPU job:**

1. Estimate `GPU-hours = wall_clock_hours x n_parallel_containers`, multiply by
   the tier's hourly rate, and present the number.
2. State GPU tier, per-container duration, and parallel-container count.
3. **Wait for explicit user approval.** If declined, offer a smaller tier, a
   fraction of the sweep, or a cheaper GPU.

Always set `timeout=` on every function so a hung container cannot bill
indefinitely. Estimation formulas, timeout/retry patterns, and Volume cleanup
are in [references/gpu-and-cost.md](references/gpu-and-cost.md).

## Building the Image

Pin a reproducible scientific stack (NumPy/SciPy + `cupy-cuda12x` for GPU
arrays, `jax[cuda12]` for differentiable work), add domain libraries only when
needed, and prefer vendor CUDA base images (e.g. NVIDIA NGC OpenMM) for tools
with heavy native dependencies. Full image recipes — core stack, molecular
dynamics, RAPIDS GPU DataFrames, and library-choice notes — are in
[references/images.md](references/images.md).

## References

- [references/patterns.md](references/patterns.md) — compute patterns: parallel
  Monte Carlo, molecular dynamics, Volume-backed sweeps, JAX PDE, multi-GPU,
  retrieving results.
- [references/gpu-and-cost.md](references/gpu-and-cost.md) — GPU tier
  trade-offs, pricing guidance, GPU-hour estimation, timeouts/retries, Volume
  lifecycle, and failure modes.
- [references/images.md](references/images.md) — scientific Image recipes and
  GPU-library selection (CuPy vs JAX vs RAPIDS, registry base images).
