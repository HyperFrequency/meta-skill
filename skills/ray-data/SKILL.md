---
name: ray-data
description: Scalable distributed data processing for ML/AI workloads with streaming execution across CPU/GPU. Reads/writes Parquet, CSV, JSON, images, NumPy; integrates with Ray Train, PyTorch, TensorFlow; scales from a laptop to 100s of nodes. Use for batch inference, distributed data preprocessing, multi-modal data loading, or larger-than-memory ETL feeding ML training. Do NOT use for small in-memory data (use pandas/polars), single-machine SQL-style analytics (use dask/duckdb), or enterprise SQL ETL (use Spark).
version: 1.0.0
author: Orchestra Research
license: MIT
tags: [Data Processing, Ray Data, Distributed Computing, ML Pipelines, Batch Inference, ETL, Scalable, Ray, PyTorch, TensorFlow]
dependencies: ["ray[data]", pyarrow, pandas]
---

# Ray Data - Scalable ML Data Processing

Distributed, streaming data processing library for ML and AI workloads.

## When to use

**Use Ray Data when:**
- Processing large (>100GB) or larger-than-memory datasets for ML
- Distributing preprocessing across a cluster
- Building batch / offline inference pipelines
- Loading multi-modal data (images, audio, video)
- Feeding distributed training (Ray Train, PyTorch, TensorFlow)

**Use something else when:**
- Small data (<1GB) in memory → pandas / polars
- Single-machine tabular / SQL-style analytics → dask (sibling skill) / duckdb
- Enterprise SQL ETL → Spark

## Quick start

```bash
pip install -U 'ray[data]'
```

```python
import ray

ds = ray.data.read_parquet("s3://bucket/data/*.parquet")   # lazy
ds = ds.map_batches(lambda b: {"text": b["text"].str.lower()})  # vectorized
for batch in ds.iter_batches(batch_size=100):               # streamed
    process(batch)
```

Core mental model: datasets are **lazy** and **streamed** as blocks, so chained
transforms fuse and data larger than memory flows through without full
materialization. Prefer `map_batches` (vectorized) over `map` (row-by-row).

## Reference docs

- **[I/O Guide](references/io.md)** — reading/writing Parquet, CSV, JSON, images, NumPy, pandas; cloud storage; supported-format matrix; streaming
- **[Transformations Guide](references/transformations.md)** — map_batches, map, filter, flat_map, groupby, GPU transforms, best practices
- **[Integration Guide](references/integration.md)** — Ray Train, PyTorch (`iter_torch_batches`/`to_torch`), TensorFlow (`to_tf`)
- **[Patterns & Performance](references/patterns.md)** — batch inference, preprocessing pipelines, repartition/batch-size tuning, benchmarks, production users

## Resources

- Docs: https://docs.ray.io/en/latest/data/data.html
- GitHub: https://github.com/ray-project/ray (36k+ stars)
- Version: Ray 2.40.0+
- Examples: https://docs.ray.io/en/latest/data/examples/overview.html
