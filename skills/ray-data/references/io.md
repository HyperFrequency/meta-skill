# Ray Data I/O Guide

Reading and writing datasets across formats and storage backends.

## Reading from cloud storage

```python
import ray

# Parquet (recommended for ML — columnar, compressed, schema-aware)
ds = ray.data.read_parquet("s3://bucket/data/*.parquet")

# CSV
ds = ray.data.read_csv("s3://bucket/data/*.csv")

# JSON / JSONL
ds = ray.data.read_json("gs://bucket/data/*.json")

# Images (returns an "image" column of ndarrays)
ds = ray.data.read_images("s3://bucket/images/")
```

Cloud paths (`s3://`, `gs://`, `az://`) are read via pyarrow/fsspec. Credentials
come from the standard provider chains (env vars, instance roles, `~/.aws`, etc.).

## Reading from Python objects

```python
# From a list of dicts
ds = ray.data.from_items([{"id": i, "value": i * 2} for i in range(1000)])

# Synthetic range (useful for benchmarks/tests)
ds = ray.data.range(1_000_000)

# From pandas
import pandas as pd
df = pd.DataFrame({"col1": [1, 2, 3], "col2": [4, 5, 6]})
ds = ray.data.from_pandas(df)
```

## Writing data

```python
ds.write_parquet("s3://bucket/output/")   # recommended
ds.write_csv("output/")
ds.write_json("output/")
```

## Supported formats

| Format  | Read | Write | Use case                  |
|---------|------|-------|---------------------------|
| Parquet | yes  | yes   | ML data (recommended)     |
| CSV     | yes  | yes   | Tabular data              |
| JSON    | yes  | yes   | Semi-structured           |
| Images  | yes  | no    | Computer vision           |
| NumPy   | yes  | yes   | Arrays                    |
| Pandas  | yes  | no    | In-memory DataFrames      |

## Streaming execution

Ray Data executes lazily and streams blocks, so datasets larger than cluster
memory are processed without ever fully materializing:

```python
ds = ray.data.read_parquet("s3://huge-dataset/")
for batch in ds.iter_batches(batch_size=1000):
    process(batch)  # streamed block-by-block, not loaded all at once
```
