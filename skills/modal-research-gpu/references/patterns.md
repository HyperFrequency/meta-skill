# Compute Patterns

Reusable patterns for scientific workloads on Modal. Each assumes:

```python
import modal
app = modal.App("research-compute")
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "numpy", "scipy", "cupy-cuda12x"
)
```

Run any of these with `modal run script.py`. Import GPU/CUDA libraries **inside**
the function (the launching process has no CUDA), and return host-side objects
(the return value is pickled back to your machine).

## Parallel Monte Carlo (fan-out)

The signature Modal win: spread independent replicates across many GPUs with
`.map()`. Each container gets a distinct seed; you aggregate the returned host
arrays.

```python
@app.function(image=image, gpu="A10G", timeout=7200)
def monte_carlo_batch(seed: int, n_samples: int, dim: int):
    import cupy as cp
    rng = cp.random.default_rng(seed)
    samples = rng.standard_normal((n_samples, dim))
    results = run_simulation_kernel(samples)   # your GPU kernel
    return cp.asnumpy(results)

@app.local_entrypoint()
def main():
    seeds = list(range(100))                   # 100 parallel containers
    batches = monte_carlo_batch.map(
        seeds,
        kwargs={"n_samples": 1_000_000, "dim": 3},
    )
    aggregate(list(batches))                    # combine on the host
```

Notes:
- `.map()` returns results in input order and streams them as they finish.
- Use `.starmap()` when each call takes several positional args.
- Cap concurrency (and therefore peak cost) by bounding the seed list and setting
  `max_containers=` on `@app.function` (or `Function.with_options(max_containers=N)`).
  Note `.map(..., order_outputs=True)` only controls output ordering — it defaults
  to True and does not limit concurrency.
- One seed → one distinct RNG stream; never reuse a seed across containers or you
  double-count.

## Molecular Dynamics (registry base image)

Tools with heavy native/CUDA dependencies are easiest from a vendor image.
Layer Python extras on top with `.pip_install(...)`.

```python
image_md = (
    modal.Image.from_registry("nvcr.io/hpc/openmm:8.1.1")
    .pip_install("mdtraj", "parmed")
)

@app.function(image=image_md, gpu="A100-40GB", timeout=14400)
def run_md_simulation(pdb_path: str, steps: int = 1_000_000):
    import openmm
    import openmm.app as omm_app
    pdb = omm_app.PDBFile(pdb_path)
    forcefield = omm_app.ForceField("amber14-all.xml", "amber14/tip3pfb.xml")
    system = forcefield.createSystem(
        pdb.topology,
        nonbondedMethod=omm_app.PME,
        nonbondedCutoff=1.0,
        constraints=omm_app.HBonds,
    )
    integrator = openmm.LangevinMiddleIntegrator(300, 1.0, 0.004)
    platform = openmm.Platform.getPlatformByName("CUDA")
    simulation = omm_app.Simulation(pdb.topology, system, integrator, platform)
    simulation.context.setPositions(pdb.positions)
    simulation.minimizeEnergy()
    simulation.step(steps)
```

Long MD runs should checkpoint trajectory frames to a Volume (below) so an
eviction or timeout does not discard hours of work.

## Volume-Backed Parameter Sweep

Persist each sweep point's output to a shared Volume, and return only a small
summary metric to the host. Call `vol.commit()` after writing so other
functions and later runs can read the file.

```python
vol = modal.Volume.from_name("research-results", create_if_missing=True)

@app.function(image=image, gpu="T4", volumes={"/results": vol}, timeout=3600)
def sweep_point(param_set: dict):
    import numpy as np
    result = run_experiment(param_set)
    np.savez(f"/results/sweep_{param_set['id']}.npz", **result)
    vol.commit()                                # flush to durable storage
    return {"id": param_set["id"], "metric": float(result["metric"])}

@app.local_entrypoint()
def sweep():
    grid = [{"id": i, "alpha": a, "beta": b}
            for i, (a, b) in enumerate(build_grid())]
    summaries = list(sweep_point.map(grid))
```

## JAX / Differentiable Scientific Computing

For gradient-based fitting, inverse problems, and stiff ODE/PDE systems, JAX +
`diffrax` gives autodiff-through-the-solver.

```python
image_jax = modal.Image.debian_slim(python_version="3.12").pip_install(
    "jax[cuda12]", "diffrax", "equinox"
)

@app.function(image=image_jax, gpu="A100-40GB", timeout=7200)
def solve_ode(k: float, t_final: float, y0: list[float]):
    import jax.numpy as jnp
    import diffrax
    def vector_field(t, y, args):
        return -args["k"] * y + jnp.sin(t)
    sol = diffrax.diffeqsolve(
        diffrax.ODETerm(vector_field),
        diffrax.Tsit5(),
        t0=0.0, t1=t_final, dt0=0.01,
        y0=jnp.asarray(y0),
        args={"k": k},
    )
    return {"t": sol.ts.tolist(), "y": sol.ys.tolist()}
```

JAX compiles on first call; keep containers warm across a sweep (reuse one
function over `.map()`) so you pay the XLA compile once per container.

## Multi-GPU on a Single Node

Ask for `count` GPUs on one machine with the `:N` suffix, then shard with
`jax.pmap` / sharded arrays or the framework's own multi-GPU path.

```python
@app.function(image=image_jax, gpu="A100-80GB:4", timeout=14400)
def multi_gpu_solve():
    import jax
    devices = jax.devices()          # 4 GPUs visible
    # split state across devices with jax.pmap / jax.sharding
    return len(devices)
```

Single-node multi-GPU is for one problem too big for one card. For many
*independent* problems, prefer `.map()` fan-out across single-GPU containers —
it is simpler and usually cheaper.

## Retrieving Results

Two ways to get data back:

1. **Return value** — pickled to the host; fine for small arrays and summaries.
2. **Volume** — for large outputs, write inside the function, `commit()`, then
   pull locally:

```python
# after the run, from your shell:
#   modal volume get research-results sweep_0.npz ./sweep_0.npz
#   modal volume ls  research-results
```

Delete a Volume you no longer need to stop paying storage:
`modal volume rm research-results`.
