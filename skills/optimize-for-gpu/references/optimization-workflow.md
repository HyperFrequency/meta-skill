# GPU Optimization Workflow

The process to follow when helping a user optimize code for the GPU.

## 1. Profile First

Before optimizing, understand where time is actually spent — use `time`, `cProfile`,
`line_profiler`, or `py-spy`. Don't guess; measure. The bottleneck might not be where
the user thinks.

## 2. Assess GPU Suitability

GPU acceleration is a good fit when:
- **Data parallelism is high**: the same operation applies to thousands/millions of elements
- **Compute intensity is high**: many FLOPs per byte of memory accessed
- **Data is large enough**: GPU overhead means small arrays (< ~10K elements) may be slower on GPU
- **Memory fits**: data must fit in GPU memory (typically 8–80 GB)

GPU is a poor fit when:
- Data is tiny (< 10K elements)
- The algorithm is inherently sequential with data dependencies between steps
- Code is I/O bound (disk, network), not compute bound — though KvikIO with GPUDirect
  Storage can help when IO feeds GPU compute
- Many small, heterogeneous operations (kernel launch overhead dominates)

## 3. Start Simple, Then Optimize

1. **Try the drop-in replacement first.** CuPy for NumPy, `cudf.pandas` for pandas,
   `cuml.accel` for sklearn, `nx-cugraph` for NetworkX. This alone often gives 5–50x.
2. **Minimize host-device transfers.** Keep data on GPU. Every PCIe transfer is expensive
   (~12 GB/s) vs GPU memory bandwidth (~900 GB/s+).
3. **Batch operations.** Fewer large GPU operations beat many small ones.
4. **Only write custom kernels if needed.** CuPy and cuDF use NVIDIA's hand-tuned libraries.
   Reserve custom Numba/Warp kernels for operations without a library equivalent.
5. **Profile the GPU version.** Use `nsys`, `ncu`, or CuPy's built-in benchmarking
   (`cupyx.profiler.benchmark`).

## 4. Memory Management Principles

These apply across all libraries:
- **Pre-allocate output arrays** instead of creating new ones in loops
- **Reuse GPU memory** — use memory pools (CuPy has this built in)
- **Use pinned (page-locked) host memory** for faster CPU-GPU transfers
- **Avoid unnecessary copies** — use in-place operations where possible
- **Stream operations** to overlap compute and data transfer

## 5. Common Pitfalls

- **Implicit CPU fallback**: some operations silently fall back to CPU. Watch for warnings.
- **Synchronization overhead**: GPU operations are asynchronous. Calling `.get()` or
  `cp.asnumpy()` forces a sync.
- **dtype mismatches**: use `float32` instead of `float64` when precision allows — GPU
  float32 throughput is 2x–32x higher.
- **Small kernel launches**: each launch has ~5–20 µs overhead. Fuse operations when possible.

## Important Correctness Notes

- Always handle the case where no GPU is available — provide a CPU fallback or a clear error.
- Test numerical correctness against CPU results (GPU floating point may differ slightly due
  to operation ordering).
- GPU memory is limited — for datasets larger than GPU memory, consider chunking or RAPIDS
  Dask for multi-GPU.
- The CUDA Array Interface enables zero-copy sharing between CuPy, Numba, Warp, cuDF, cuML,
  cuGraph, cuVS, cuCIM, cuSpatial, KvikIO, PyTorch, and JAX arrays on GPU.

## Combining Libraries

Many real workloads use multiple libraries together. They interoperate via the CUDA Array
Interface — zero-copy data sharing between CuPy, Numba, Warp, cuDF, cuML, cuGraph, cuVS,
cuCIM, cuSpatial, KvikIO, PyTorch, JAX, and other GPU libraries.

Common combinations:
- **cuDF + cuML**: load/preprocess with cuDF, train/predict with cuML — the full RAPIDS pipeline
- **cuDF + cuGraph**: build graphs from cuDF edge lists, run analytics with cuGraph
- **cuGraph + cuML**: extract graph features with cuGraph, feed into cuML
- **cuML + cuVS**: train an embedding model with cuML, index/search embeddings with cuVS
- **cuDF + CuPy**: load/filter with cuDF, numerical analysis with CuPy
- **CuPy + cuVS**: generate embeddings with CuPy ops, build a cuVS index — zero-copy
- **Warp + PyTorch**: differentiable simulation in Warp, backprop into a PyTorch training loop
- **Warp + CuPy**: CuPy for array math, Warp for spatial queries (mesh, volume) — zero-copy
- **Warp + JAX**: Warp kernels as JAX primitives inside jitted functions
- **CuPy + Numba**: CuPy for standard ops, drop into Numba for custom kernels
- **cuDF + Numba**: process dataframes with cuDF, apply custom GPU functions via Numba UDFs
- **cuML + CuPy**: train with cuML, custom post-processing with CuPy
- **cuDF + cuxfilter**: load with cuDF, build interactive cross-filtering dashboards
- **cuML + cuxfilter**: run ML (UMAP, clustering) with cuML, visualize interactively
- **cuGraph + cuxfilter**: graph analytics with cuGraph, visualize with cuxfilter's graph chart
- **cuCIM + CuPy**: cuCIM operates on CuPy arrays natively — chain image processing with math
- **cuCIM + PyTorch**: preprocess with cuCIM, pass to PyTorch via DLPack — zero-copy
- **cuCIM + cuML**: extract image features (regionprops) with cuCIM, train classifiers with cuML
- **KvikIO + CuPy**: load raw binary directly into CuPy arrays via GDS, bypassing CPU memory
- **KvikIO + Numba**: read directly to GPU with KvikIO, process with custom Numba kernels
- **KvikIO + Zarr**: GDSStore backend reads/writes chunked N-dimensional arrays on GPU
- **cuSpatial + cuDF**: load geospatial data with cuDF, do spatial joins/analysis with cuSpatial
- **cuSpatial + cuML**: extract spatial features with cuSpatial, train ML models with cuML
- **RAFT + CuPy**: use RAFT's `eigsh()` on sparse matrices built with `cupyx.scipy.sparse`
- **RAFT + raft-dask**: scale GPU workloads across multiple GPUs/nodes via Dask
