# GPU Selection, Cost, and Ops

## GPU Tiers

Modal exposes GPUs as strings on `@app.function(gpu=...)`. Accepted forms:

- Bare type: `gpu="A10G"`, `gpu="H100"`, `gpu="L4"`, `gpu="T4"`, `gpu="L40S"`.
- Memory-qualified: `gpu="A100-40GB"`, `gpu="A100-80GB"` (bare `"A100"` defaults
  to the 40 GB variant — be explicit).
- With a count for single-node multi-GPU: `gpu="A100-80GB:4"`.

| Tier | VRAM | Strengths | Typical use |
|------|------|-----------|-------------|
| `T4` | 16 GB | Cheapest, always available | Tests, light numerics, small MC |
| `L4` | 24 GB | Efficient, good FP32 | Medium simulations, data processing |
| `A10G` | 24 GB | Balanced default | General scientific computing |
| `L40S` | 48 GB | Large FP32 + memory | Big single-card simulations |
| `A100-40GB` | 40 GB | High memory bandwidth | Molecular dynamics, large solves |
| `A100-80GB` | 80 GB | Largest state per card | Multi-physics, huge state spaces |
| `H100` | 80 GB | Highest throughput | Large-scale Monte Carlo, max FLOPs |

Rule of thumb: **start on `A10G`**, confirm correctness at small problem size,
and move up a tier only when you actually run out of VRAM or throughput. Doubling
the GPU tier roughly doubles the hourly rate, so scaling up must pay for itself
in wall-clock reduction.

## Cost Estimation

Modal bills per GPU-second of container run time (plus small storage/egress).
Estimate before you launch:

```
GPU-hours   = per_container_wall_clock_hours x n_parallel_containers
job_cost    = GPU-hours x tier_hourly_rate
```

A 100-way `.map()` where each container runs 20 minutes on a tier costing
~$1.10/hr is `(20/60) x 100 x 1.10 ≈ $37` — not `$1.10`. Fan-out multiplies cost
by container count; that is the number to present for approval.

**Hourly rates change and vary by region.** Do not hard-code them. Check the
current Modal pricing page (or `modal` dashboard) at estimation time. As a rough
*relative* ordering, cost climbs T4 < L4 < A10G < L40S < A100-40GB < A100-80GB <
H100, with H100 typically several times a T4's rate.

## Mandatory Cost-Approval Gate

Before launching any paid GPU job:

1. Present the estimate: GPU tier, per-container duration, parallel-container
   count, and the resulting dollar figure.
2. Wait for **explicit** user approval — never auto-launch a large fan-out.
3. If declined, offer a cheaper tier, a smaller subset of the sweep, or a dry
   run on `T4` at reduced problem size to validate correctness first.

Spot-check discipline: run one container (or a handful) end-to-end, verify the
numbers are physically sensible, *then* scale to the full sweep.

## Timeouts and Retries

- **Always set `timeout=`** (seconds) on every function. A hung kernel or an
  infinite loop otherwise bills until the platform default cutoff. Match it to a
  realistic upper bound of the job, not a round guess.
- Add `retries=` for transient failures (image pull, spot eviction), but keep
  retries low for expensive containers — a flaky 4-hour A100 job that retries 3x
  is a 16-GPU-hour surprise.
- `Function.with_options(gpu=..., timeout=..., max_containers=...)` lets you
  reconfigure a function at call time without redefining it — handy for reusing
  one definition across a cheap test run and an expensive full run.

## Volume Lifecycle

- Create once, reuse by name: `modal.Volume.from_name("name",
  create_if_missing=True)`.
- Inside a function, after writing files, call `vol.commit()` to make them
  durable and visible to other functions.
- Reads see the committed state at container start; call `vol.reload()` to pick
  up commits made by other containers mid-run.
- Inspect and pull from the shell: `modal volume ls <name>`,
  `modal volume get <name> <remote> <local>`.
- **Delete when done** to stop storage charges: `modal volume rm <name>`.

## Failure Modes and Boundaries

- **CUDA import at module top** → `ImportError` on your local machine, which has
  no GPU. Import GPU libraries inside the function body.
- **Returning device arrays** (a raw `cupy`/`jax` array) → pickling error or a
  slow implicit transfer. Convert to host (`cp.asnumpy`, `np.asarray`,
  `.tolist()`) before returning.
- **CUDA / driver mismatch** → pin the CUDA-matched wheel (`cupy-cuda12x`,
  `jax[cuda12]`) for the image's CUDA version, or use a vendor CUDA base image.
- **Cold starts** — first call on a new image pays image-build/pull and (for JAX)
  XLA compile latency. Amortize by fanning out many calls over warm containers
  rather than one call per `modal run`.
- **Fan-out cost blow-up** — the most common expensive mistake is multiplying a
  per-container cost by hundreds of containers without noticing. The approval
  gate exists to catch exactly this.
- **Not a training loop** — for gradient-descent model training use
  `distributed-training`/`fine-tuning`; for serving use `inference-serving`.
