---
name: optimize-for-gpu
version: 0.1.0
description: "GPU-accelerate Python with CuPy, Numba CUDA, Warp, and RAPIDS (cuDF, cuML, cuGraph, cuVS, cuCIM, cuSpatial, cuxfilter, KvikIO, RAFT). Use when the user mentions GPU/CUDA/NVIDIA acceleration, or wants to speed up NumPy, pandas, scikit-learn, scikit-image, NetworkX, GeoPandas, Faiss, or CPU-bound loops/large-array/ML/graph/image workloads — even if GPU is not explicitly requested. Covers array math, custom kernels, physics/differentiable simulation, dataframes, ML, graph analytics, vector search, GPUDirect Storage IO, dashboards, geospatial, imaging, and sparse eigensolvers. WHEN NOT: data is tiny (<10K elements), the algorithm is inherently sequential, the workload is pure I/O with no GPU compute, no NVIDIA GPU is available, or the user wants generic CPU refactoring/profiling without GPU porting — route those elsewhere."
metadata: {"version": "1.0", "author": "K-Dense, Inc."}
---

# GPU Optimization for Python with NVIDIA

Help users write new GPU-accelerated code, or transform CPU-bound Python to run on NVIDIA
GPUs — often 10x–1000x faster for suitable workloads. This file is a router: pick the right
library, then **read the matching reference file before writing any GPU code.**

## When This Skill Applies

Numerical/scientific Python on large arrays, matrices, or dataframes; mentions of CUDA / GPU /
NVIDIA / parallel computing; or CPU-bound code in any of these domains:

- Array/linear-algebra/FFT/signal/Monte-Carlo math (NumPy, SciPy) → **CuPy**
- Custom per-element logic, stencils, custom reductions, shared-memory kernels → **Numba**
- Physics/cloth/fluids/particles, mesh/SDF/ray-cast, robotics, differentiable sim → **Warp**
- DataFrame ETL, groupby, joins, CSV/Parquet (pandas) → **cuDF**
- ML training/inference/preprocessing, clustering, UMAP/t-SNE (scikit-learn) → **cuML**
- Centrality, community detection, PageRank, shortest paths (NetworkX) → **cuGraph**
- ANN / nearest-neighbor / similarity / RAG retrieval (Faiss, Annoy, ScaNN) → **cuVS**
- Image filtering, morphology, segmentation, WSI / digital pathology (scikit-image) → **cuCIM**
- Point-in-polygon, spatial joins, trajectories, haversine (GeoPandas) → **cuSpatial**
- Interactive cross-filter dashboards / EDA on millions of rows → **cuxfilter**
- Loading binary files / S3 / HTTP straight into GPU memory, GPUDirect Storage → **KvikIO**
- Sparse eigensolvers, device memory, multi-GPU primitives → **RAFT**

When unsure, ask what the code actually does rather than guessing the library.

## Decision Framework: Which Library

| Library | Replaces / for | Read | Use when |
|---------|----------------|------|----------|
| **CuPy** | NumPy / SciPy | `references/cupy.md` | Array math, linear algebra, FFT, sorting, reductions, sparse, signal/image filtering. Often a drop-in `import cupy as cp`. Wraps cuBLAS/cuFFT/cuSOLVER/cuSPARSE/cuRAND. |
| **Numba CUDA** | custom kernels | `references/numba.md` | Algorithms that don't map to array ops; thread/block/shared-memory control; `@vectorize(target='cuda')`; stencils, custom reductions. Compiles Python → CUDA. |
| **Warp** | simulation / spatial | `references/warp.md` | Physics (DEM/SPH/fluids/cloth/rigid bodies), mesh ray-cast, SDF, robotics, differentiable sim. JIT `@wp.kernel` with vec3/quat/Mesh/Volume/BVH; auto-differentiable. |
| **cuDF** | pandas | `references/cudf.md` | DataFrame filter/groupby/join/aggregation, CSV/Parquet/JSON, ETL. `cudf.pandas` gives zero-change acceleration. |
| **cuML** | scikit-learn | `references/cuml.md` | Classification, regression, clustering, dim-reduction, preprocessing, FIL tree inference, UMAP/t-SNE/HDBSCAN/KNN. `cuml.accel` is zero-change; 2–600x. |
| **cuGraph** | NetworkX | `references/cugraph.md` | PageRank, betweenness, Louvain/Leiden, BFS/SSSP, connected components on 10K+ edges. `nx-cugraph` backend is zero-change; 10–500x+. |
| **cuVS** | Faiss / Annoy / ScaNN | `references/cuvs.md` | ANN search, RAG retrieval, recommenders, k-NN graphs. CAGRA/IVF-Flat/IVF-PQ/brute-force + HNSW. Start with CAGRA. (Vector search migrated here from RAFT.) |
| **cuCIM** | scikit-image | `references/cucim.md` | Filtering, morphology, segmentation, regionprops, color conversion, WSI reading. `cucim.skimage` mirrors skimage (200+ fns) on CuPy arrays. |
| **cuSpatial** | GeoPandas / shapely | `references/cuspatial.md` | Point-in-polygon, spatial joins, quadtree indexing, haversine, trajectory analysis. Convert via `cuspatial.from_geopandas()`. |
| **cuxfilter** | dashboards | `references/cuxfilter.md` | Interactive cross-filtering / EDA on millions of GPU-resident rows; Bokeh + Datashader + Deck.gl + Panel. |
| **KvikIO** | file IO to GPU | `references/kvikio.md` | Raw binary / S3 / HTTP / Zarr straight into GPU memory via GPUDirect Storage (falls back to POSIX). For CSV/Parquet/JSON use cuDF's readers instead. |
| **RAFT** (pylibraft) | low-level primitives | `references/raft.md` | Sparse eigensolvers (`eigsh`), device memory, R-MAT generation, multi-GPU via `raft-dask`. Prefer cuML/cuGraph first. |

**Warp vs Numba:** both compile Python to CUDA. Warp gives higher-level spatial types
(vec3, quat, Mesh, Volume) and autodiff — use it for simulation/geometry. Numba gives raw
CUDA control (shared memory, block/thread management, atomics) — use it for general kernels.

Libraries interoperate zero-copy via the CUDA Array Interface and combine into full pipelines
(e.g. cuDF → cuML, Warp → PyTorch). See `references/optimization-workflow.md` for the full
combination list.

## Installation

Always install with `uv add` (never `pip install`/`conda install`) unless the project uses a
different manager. Full per-library install commands, CUDA-version notes, accelerator-mode
launch flags, and verification snippets are in **`references/installation.md`**.

## Optimization Workflow

The full process — profile first, assess GPU suitability, start with drop-in replacements,
memory-management principles, and common pitfalls — is in
**`references/optimization-workflow.md`**. Read it before optimizing existing code.

Quick rule of thumb: GPU wins on high data-parallelism + high compute-intensity + large data
that fits in GPU memory; it loses on tiny (<10K element), sequential, or pure-I/O workloads.

## Code Transformation Patterns

Before/after templates for every supported migration (NumPy→CuPy, pandas→cuDF, loop→Numba,
NetworkX→cuGraph, sklearn→cuML, sim→Warp, IO→KvikIO, plots→cuxfilter, skimage→cuCIM,
GeoPandas→cuSpatial, Faiss→cuVS, scipy.sparse→RAFT) are in
**`references/transformation-patterns.md`**.

## Reference Files

| File | When to read |
|------|--------------|
| `references/cupy.md` | NumPy/SciPy code or array operations on GPU |
| `references/numba.md` | Custom CUDA kernels, fine-grained GPU control, GPU ufuncs |
| `references/cudf.md` | pandas code or dataframe operations on GPU |
| `references/cuml.md` | scikit-learn code or ML training/inference/preprocessing on GPU |
| `references/cugraph.md` | NetworkX code or graph analytics on GPU |
| `references/warp.md` | GPU simulation, spatial computing, mesh/volume, differentiable programming, robotics |
| `references/kvikio.md` | High-performance file IO to/from GPU, GPUDirect Storage, S3/HTTP, Zarr |
| `references/cuxfilter.md` | GPU interactive dashboards, cross-filtering, EDA visualization |
| `references/cucim.md` | scikit-image code, image processing, digital pathology, WSI reading |
| `references/cuvs.md` | Vector search, nearest neighbors, similarity search, RAG retrieval |
| `references/cuspatial.md` | GeoPandas/shapely code, spatial joins, distance, trajectory analysis |
| `references/raft.md` | Sparse eigensolvers, device memory, multi-GPU primitives |
| `references/installation.md` | Install commands, accelerator-mode flags, CUDA verification |
| `references/optimization-workflow.md` | Profiling, GPU-suitability, memory management, pitfalls, library combinations |
| `references/transformation-patterns.md` | CPU→GPU before/after code templates |

Read the specific reference before writing code — each contains detailed API patterns,
optimization techniques, and library-specific pitfalls.
