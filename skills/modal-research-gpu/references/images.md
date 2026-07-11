# Building Scientific Images

A Modal Image is a pinned, reproducible container definition. Build it once per
app; Modal caches layers so rebuilds are fast when nothing changed.

## Core Scientific Stack

Start from `debian_slim` and layer a pinned scientific stack. Add domain
libraries only when a workload needs them — a leaner image cold-starts faster.

```python
import modal

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        # Core numerics
        "numpy>=2.0", "scipy>=1.14", "pandas>=2.2",
        # GPU arrays — drop-in NumPy replacement on CUDA 12
        "cupy-cuda12x>=13.0",
        # Differentiable computing (autodiff, XLA)
        "jax[cuda12]>=0.4.30",
        # Figures (if the job emits plots)
        "matplotlib>=3.9",
    )
)
```

Pin versions. An unpinned image can silently change numerical results between
runs when a dependency updates, which is fatal for reproducible research.

## GPU Library Selection

Pick the GPU library by what you are computing — they are not interchangeable:

- **CuPy** (`cupy-cuda12x`) — a near drop-in NumPy/SciPy replacement on GPU. Best
  when you have existing NumPy array code (linear algebra, FFTs, elementwise
  simulation kernels) and want it on the GPU with minimal rewrite.
- **JAX** (`jax[cuda12]`) — autodiff + XLA compilation. Best for gradient-based
  fitting, inverse problems, and ODE/PDE solvers where you need derivatives
  through the computation (`diffrax`, `equinox`, `optimistix`).
- **RAPIDS** (`cudf`, `cuml`) — GPU DataFrames and classical ML on tabular data.
  Best for large-scale data processing that is DataFrame-shaped rather than
  array-shaped. Easiest from the RAPIDS registry image (below).
- **PyCUDA / raw CUDA** — only when you need a hand-written kernel that none of
  the above expresses. Rarely necessary for research workloads.

Match the CUDA suffix to the image's CUDA toolkit: `cupy-cuda12x` and
`jax[cuda12]` both target CUDA 12. Mixing CUDA 11 wheels into a CUDA 12 image
produces load-time driver errors.

## Domain-Specific Base Images

For tools with heavy native/CUDA build dependencies, start from a vendor image
via `from_registry` and add only Python extras. This avoids fragile source
builds.

Molecular dynamics (OpenMM from NVIDIA NGC):

```python
image_md = (
    modal.Image.from_registry("nvcr.io/hpc/openmm:8.1.1")
    .pip_install("mdtraj", "parmed")
)
```

GPU DataFrames / classical ML (RAPIDS):

```python
image_rapids = modal.Image.from_registry(
    "nvcr.io/nvidia/rapidsai/base:24.10-cuda12.5-py3.12"
)
```

Other common registry bases: `nvcr.io/nvidia/cuda:*` for a bare CUDA toolkit you
build on top of, and framework images (LAMMPS, GROMACS) published by their
projects. Confirm the tag exists and its CUDA version matches your GPU tier
before relying on it.

## Layering Tips

- Order layers cheap-to-expensive: put rarely-changing base installs first and
  fast-changing app code last, so edits reuse cached lower layers.
- Add local source with `.add_local_python_source(...)` /
  `.add_local_dir(...)` for your own modules rather than baking them into
  `pip_install`.
- Set image-wide environment with `.env({...})` (e.g. thread caps,
  `XLA_PYTHON_CLIENT_MEM_FRACTION`) instead of inside every function.
- Keep one image per distinct dependency set. Don't union every domain's
  libraries into one giant image — it slows cold starts and invites version
  conflicts.
